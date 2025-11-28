const projectType = document.getElementById('projectType');
const newConstructionFields = document.getElementById('newConstructionFields');
const renovationFields = document.getElementById('renovationFields');
const demolitionFields = document.getElementById('demolitionFields');
const additionFields = document.getElementById('additionFields');

projectType?.addEventListener('change', () => {
    newConstructionFields.classList.add('hidden');
    renovationFields.classList.add('hidden');
    demolitionFields.classList.add('hidden');
    additionFields.classList.add('hidden');

    switch (projectType?.value) {
        case 'new_construction':
            newConstructionFields.classList.remove('hidden');
            break;
        case 'renovation':
            renovationFields.classList.remove('hidden');
            break;
        case 'demolition':
            demolitionFields.classList.remove('hidden');
            break;
        case 'addition':
            additionFields.classList.remove('hidden');
            break;
        default:
            break;
    }
});
