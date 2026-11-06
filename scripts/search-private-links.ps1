<#
.SYNOPSIS
  Manage Azure AI Search shared private links and the Search managed identity's permissions
  on the resources it calls (Azure OpenAI / Cognitive Services, Storage).

.DESCRIPTION
  Azure AI Search runs indexers, skillsets and vectorizers from its own infrastructure, not from
  your VNet. When the target (OpenAI, Storage) has public access disabled, Search needs:
    1. A shared private link (Search-managed private endpoint) to the target, approved on the
       target side.
    2. A role for the Search system-assigned identity on the target, e.g.
       "Cognitive Services OpenAI User" or "Storage Blob Data Reader", when the skillset /
       vectorizer / data source authenticates with managed identity (no key).

  A shared private link shows "Disconnected" when the connection on the target was deleted or
  the target itself was deleted. It never recovers on its own: delete it and create a new one.

  Load the functions, then call them:
    . .\scripts\search-private-links.ps1

  Requires the Azure CLI, logged in (az login) with rights on the Search service and the target.

.EXAMPLE
  . .\scripts\search-private-links.ps1
  $search = @{ Subscription = 'd94cca-dev - CSS AI POC'; ResourceGroup = 'd94cca-dev-networking'; SearchService = 'css-ai-dev-aisearch' }

  # 1. View private links (all, or only the broken ones)
  Get-SearchPrivateLink @search
  Get-SearchPrivateLink @search -DisconnectedOnly

  # 2. Delete one (asks for confirmation; -WhatIf shows what would happen)
  Remove-SearchPrivateLink @search -Name 'Search-OpenAI-sharedprivatelink'

  # 3. Create and approve a new one
  $openai = '/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account>'
  New-SearchPrivateLink @search -Name 'search-openai-spl' -TargetResourceId $openai -GroupId openai_account
  # (cross-subscription / no rights on the target: approve in the portal instead)

  # 4. View the Search identity's permissions (everywhere, or on one target)
  Get-SearchIdentityRole @search
  Get-SearchIdentityRole @search -Scope $openai

  # 5. Grant Cognitive Services OpenAI User on the OpenAI account
  Add-SearchIdentityRole @search -Scope $openai -Role 'Cognitive Services OpenAI User'
#>

# Shared private link group IDs by target type
#   Azure OpenAI / AI Services : openai_account   (AIServices accounts can also use cognitiveservices_account)
#   Storage (blob)             : blob
#   Storage (ADLS Gen2)        : dfs
#   Cosmos DB (SQL API)        : Sql
#   Key Vault                  : vault

# Search management API version used to create shared private links (supports openai_account).
$SearchApiVersion = '2024-06-01-preview'

function Invoke-Az {
    # Runs az, fails on a non-zero exit code, returns parsed JSON (or $null for empty output).
    param([Parameter(Mandatory)][string[]]$Arguments)
    $output = & az @Arguments --only-show-errors
    if ($LASTEXITCODE -ne 0) {
        throw "az $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
    $text = ($output | Out-String).Trim()
    if ($text) { return $text | ConvertFrom-Json }
    return $null
}

function Get-SearchServiceInfo {
    param(
        [Parameter(Mandatory)][string]$Subscription,
        [Parameter(Mandatory)][string]$ResourceGroup,
        [Parameter(Mandatory)][string]$SearchService
    )
    Invoke-Az @('search', 'service', 'show', '--subscription', $Subscription,
        '--resource-group', $ResourceGroup, '--name', $SearchService, '-o', 'json')
}

# -------------
# 1. View private links
# -------------
function Get-SearchPrivateLink {
    <#
      Lists the Search service's shared private links. Status:
        Pending      - waiting for approval on the target
        Approved     - usable
        Rejected     - rejected on the target
        Disconnected - connection removed on the target, or the target was deleted
      TargetExists = False means the target resource no longer exists.
    #>
    param(
        [Parameter(Mandatory)][string]$Subscription,
        [Parameter(Mandatory)][string]$ResourceGroup,
        [Parameter(Mandatory)][string]$SearchService,
        [switch]$DisconnectedOnly
    )
    $links = Invoke-Az @('search', 'shared-private-link-resource', 'list', '--subscription', $Subscription,
        '--resource-group', $ResourceGroup, '--service-name', $SearchService, '-o', 'json')

    $result = foreach ($link in @($links)) {
        if (-not $link) { continue }
        $target = $link.properties.privateLinkResourceId
        & az resource show --ids $target --only-show-errors -o none 2>$null
        $exists = ($LASTEXITCODE -eq 0)
        [pscustomobject]@{
            Name             = $link.name
            GroupId          = $link.properties.groupId
            Status           = $link.properties.status
            Provisioning     = $link.properties.provisioningState
            TargetExists     = $exists
            TargetResourceId = $target
        }
    }
    if ($DisconnectedOnly) {
        $result = $result | Where-Object { $_.Status -ne 'Approved' -or -not $_.TargetExists }
    }
    $result
}

# -------------
# 2. Delete a private link
# -------------
function Remove-SearchPrivateLink {
    # Deletes a shared private link. Skillsets / data sources that rely on it stop working until a
    # replacement is created and approved.
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
    param(
        [Parameter(Mandatory)][string]$Subscription,
        [Parameter(Mandatory)][string]$ResourceGroup,
        [Parameter(Mandatory)][string]$SearchService,
        [Parameter(Mandatory)][string]$Name
    )
    if ($PSCmdlet.ShouldProcess("$SearchService/$Name", 'Delete shared private link')) {
        Invoke-Az @('search', 'shared-private-link-resource', 'delete', '--subscription', $Subscription,
            '--resource-group', $ResourceGroup, '--service-name', $SearchService, '--name', $Name, '--yes') | Out-Null
        Write-Host "Deleted shared private link $Name"
    }
}

# -------------
# 3. Create (enable) a private link and approve it
# -------------
function New-SearchPrivateLink {
    <#
      Creates a shared private link from Search to TargetResourceId, waits for it to be provisioned,
      then approves the pending connection on the target (needs rights on the target; use
      -SkipApproval and approve in the portal otherwise: target > Networking > Private endpoint
      connections).
    #>
    param(
        [Parameter(Mandatory)][string]$Subscription,
        [Parameter(Mandatory)][string]$ResourceGroup,
        [Parameter(Mandatory)][string]$SearchService,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$TargetResourceId,
        [Parameter(Mandatory)][ValidateSet('openai_account', 'cognitiveservices_account', 'blob', 'dfs', 'Sql', 'vault')][string]$GroupId,
        [string]$RequestMessage = "Azure AI Search $SearchService access",
        [switch]$SkipApproval
    )
    Write-Host "Creating shared private link $Name ($GroupId) -> $TargetResourceId (takes a few minutes)..."
    # "az search shared-private-link-resource create" uses an older API version that rejects
    # openai_account, so call the management API directly with a version that supports it.
    $searchId = (Get-SearchServiceInfo -Subscription $Subscription -ResourceGroup $ResourceGroup -SearchService $SearchService).id
    $url = "https://management.azure.com$searchId/sharedPrivateLinkResources/${Name}?api-version=$SearchApiVersion"
    $bodyFile = [System.IO.Path]::GetTempFileName()
    try {
        @{ properties = @{ privateLinkResourceId = $TargetResourceId; groupId = $GroupId; requestMessage = $RequestMessage } } |
            ConvertTo-Json -Depth 5 | Set-Content -Path $bodyFile -Encoding ascii
        Invoke-Az @('rest', '--method', 'put', '--url', $url, '--body', "@$bodyFile",
            '--headers', 'Content-Type=application/json', '-o', 'none') | Out-Null
    }
    finally {
        Remove-Item $bodyFile -ErrorAction SilentlyContinue
    }

    # The PUT is asynchronous; wait for provisioning to finish.
    $deadline = (Get-Date).AddMinutes(20)
    do {
        Start-Sleep -Seconds 20
        $state = (Invoke-Az @('rest', '--method', 'get', '--url', $url, '-o', 'json')).properties.provisioningState
        Write-Host "  provisioningState: $state"
    } while ($state -notin @('Succeeded', 'Failed') -and (Get-Date) -lt $deadline)
    if ($state -ne 'Succeeded') { throw "Shared private link $Name did not provision (state: $state)." }

    if ($SkipApproval) {
        Write-Host "Created. Approve the pending connection on the target in the portal."
        return
    }
    Approve-PrivateLinkConnection -TargetResourceId $TargetResourceId -RequestMessage $RequestMessage
    Get-SearchPrivateLink -Subscription $Subscription -ResourceGroup $ResourceGroup -SearchService $SearchService |
        Where-Object Name -eq $Name
}

function Approve-PrivateLinkConnection {
    # Approves pending private endpoint connections on the target that carry RequestMessage.
    param(
        [Parameter(Mandatory)][string]$TargetResourceId,
        [Parameter(Mandatory)][string]$RequestMessage
    )
    $connections = Invoke-Az @('network', 'private-endpoint-connection', 'list', '--id', $TargetResourceId, '-o', 'json')
    $pending = @($connections) | Where-Object {
        $_ -and
        $_.properties.privateLinkServiceConnectionState.status -eq 'Pending' -and
        $_.properties.privateLinkServiceConnectionState.description -eq $RequestMessage
    }
    if (-not $pending) {
        Write-Host "No pending connection with message '$RequestMessage' on the target (already approved?)."
        return
    }
    foreach ($connection in $pending) {
        Write-Host "Approving $($connection.id)"
        Invoke-Az @('network', 'private-endpoint-connection', 'approve', '--id', $connection.id,
            '--description', 'Approved for Azure AI Search', '-o', 'none') | Out-Null
    }
}

# -------------
# 4. View the Search identity's permissions
# -------------
function Get-SearchIdentityRole {
    # Lists role assignments of the Search system-assigned identity, everywhere or on one Scope.
    param(
        [Parameter(Mandatory)][string]$Subscription,
        [Parameter(Mandatory)][string]$ResourceGroup,
        [Parameter(Mandatory)][string]$SearchService,
        [string]$Scope
    )
    $principalId = (Get-SearchServiceInfo -Subscription $Subscription -ResourceGroup $ResourceGroup -SearchService $SearchService).identity.principalId
    if (-not $principalId) { throw "$SearchService has no system-assigned identity. Enable it under Search > Identity." }

    $arguments = @('role', 'assignment', 'list', '--assignee', $principalId, '--subscription', $Subscription, '-o', 'json')
    if ($Scope) { $arguments += @('--scope', $Scope, '--include-inherited') } else { $arguments += '--all' }

    $assignments = Invoke-Az $arguments
    if (-not $assignments) {
        Write-Host "No role assignments for $SearchService identity $principalId$(if ($Scope) { " on $Scope" })."
        return
    }
    $assignments | ForEach-Object {
        [pscustomobject]@{ Role = $_.roleDefinitionName; Scope = $_.scope; PrincipalId = $principalId }
    }
}

# -------------
# 5. Grant the Search identity a role (e.g. Cognitive Services OpenAI User)
# -------------
function Add-SearchIdentityRole {
    <#
      Common roles for Search:
        Cognitive Services OpenAI User - call embedding / chat deployments (vectorizer, embedding skill)
        Cognitive Services User        - AI Services skills (OCR, language, ...) on a multi-service account
        Storage Blob Data Reader       - blob data source with "ResourceId=<storage id>;"
      Needs Owner, User Access Administrator or Role Based Access Control Administrator on Scope.
      Role assignments can take a few minutes to take effect.
    #>
    param(
        [Parameter(Mandatory)][string]$Subscription,
        [Parameter(Mandatory)][string]$ResourceGroup,
        [Parameter(Mandatory)][string]$SearchService,
        [Parameter(Mandatory)][string]$Scope,
        [string]$Role = 'Cognitive Services OpenAI User'
    )
    $principalId = (Get-SearchServiceInfo -Subscription $Subscription -ResourceGroup $ResourceGroup -SearchService $SearchService).identity.principalId
    if (-not $principalId) { throw "$SearchService has no system-assigned identity. Enable it under Search > Identity." }

    $existing = Invoke-Az @('role', 'assignment', 'list', '--assignee', $principalId, '--scope', $Scope,
        '--role', $Role, '--subscription', $Subscription, '-o', 'json')
    if ($existing) {
        Write-Host "'$Role' already assigned to $SearchService on $Scope."
        return
    }
    Invoke-Az @('role', 'assignment', 'create', '--assignee-object-id', $principalId,
        '--assignee-principal-type', 'ServicePrincipal', '--role', $Role, '--scope', $Scope,
        '--subscription', $Subscription, '-o', 'none') | Out-Null
    Write-Host "Assigned '$Role' to $SearchService ($principalId) on $Scope."
}
