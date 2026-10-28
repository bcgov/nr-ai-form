/**
 * captureFormValues(root, options)
 *
 * Collects the current value of every control carrying a `data-id` attribute
 * and returns a plain object keyed by that `data-id`.
 *
 * Controls that share a `data-id` (radio groups, checkbox groups) are resolved
 * as a single logical field rather than overwriting each other.
 *
 * Returned shapes:
 *   text / textarea / date / number / etc. -> string
 *   radio group                            -> string of the checked option, or null
 *   single checkbox                        -> boolean (or its value / null if it has a value attr)
 *   checkbox group                         -> array of checked values (empty array if none)
 *   single select                          -> string
 *   multi select                           -> array of selected values
 */
function captureFormValues(root = document, options = {}) {
  const {
    includeDisabled = false, // disabled controls are excluded by default (they don't submit)
    skipTypes = ['password', 'submit', 'button', 'reset', 'image', 'file'],
  } = options;

  // 1. Bucket every tagged control by its data-id, preserving DOM order.
  const groups = new Map();

  root.querySelectorAll('input[data-id], select[data-id], textarea[data-id]').forEach((el) => {
    if (!includeDisabled && el.disabled) return;
    if (el.tagName === 'INPUT' && skipTypes.includes(el.type)) return;

    const key = el.dataset.id;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(el);
  });

  // 2. Resolve each bucket to a single value.
  const values = {};
  groups.forEach((els, key) => {
    values[key] = readGroup(els);
  });

  return values;
}

/**
 * Resolves one data-id bucket (one or more elements) to a value.
 */
function readGroup(els) {
  const first = els[0];
  const type = first.tagName === 'INPUT' ? first.type : first.tagName.toLowerCase();

  switch (type) {
    // Radios: exactly one value per group, null when nothing is selected.
    case 'radio': {
      const checked = els.find((el) => el.checked);
      return checked ? radioOrCheckboxValue(checked) : null;
    }

    // Checkboxes: a group yields an array, a lone checkbox yields a boolean
    // unless it carries an explicit value (then value-or-null keeps the meaning).
    case 'checkbox': {
      if (els.length > 1) {
        return els.filter((el) => el.checked).map(radioOrCheckboxValue);
      }
      const hasExplicitValue = first.hasAttribute('value');
      if (!hasExplicitValue) return first.checked;
      return first.checked ? first.value : null;
    }

     // Selects: capture the option label, not the underlying numeric key.
    // An option with an empty value is a placeholder ("(select)"), so it reads
    // as an empty string rather than leaking the placeholder text.
    case 'select': {
      const selected = Array.from(first.selectedOptions).filter((opt) => opt.value !== '');
 
      if (first.multiple) {
        return selected.map(optionLabel);
      }
      return selected.length ? optionLabel(selected[0]) : '';
    }

    // Everything else (text, email, tel, number, date, range, hidden, textarea)
    // reads as a plain value. Only the first match is read — a duplicated
    // data-id here is a markup bug, not a group.
    default:
      return first.value;
  }
}

/**
 * The human-readable label of an option, whitespace collapsed.
 */
function optionLabel(opt) {
  return (opt.label || opt.text || '').replace(/\s+/g, ' ').trim();
}

/**
 * Radios/checkboxes with no value attribute submit as "on" in a real form,
 * so mirror that instead of returning an empty string.
 */
function radioOrCheckboxValue(el) {
  return el.hasAttribute('value') ? el.value : 'on';
}

// Usage:
//   const data = captureFormValues();                     // whole document
//   const data = captureFormValues(document.querySelector('#step2')); // one step
//   const data = captureFormValues(document, { includeDisabled: true });

export { captureFormValues };

// const data = captureFormValues();
// console.clear();
// console.log(data);