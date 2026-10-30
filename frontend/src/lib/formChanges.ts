// Read controls directly, including disabled fields: FormData omits them during saves.
export function formSnapshot(form: HTMLFormElement, initial = false): string {
  const values: Record<string, unknown[]> = {};
  const sets = new Set<string>();
  for (const field of form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input, select, textarea')) {
    if (!field.name || field.hasAttribute('data-dirty-ignore')) continue;
    let value: unknown = field.value;
    if (field instanceof HTMLInputElement) {
      if (['button', 'submit', 'reset'].includes(field.type)) continue;
      if (field.type === 'checkbox' || field.type === 'radio') value = field.checked ? field.value : null;
      else if (field.type === 'number') value = field.value === '' ? '' : field.valueAsNumber;
      else if (field.type === 'file') value = Array.from(field.files ?? [], file => [file.name, file.size, file.type, file.lastModified]);
    }
    if (initial && field.dataset.initialValue !== undefined) value = field.dataset.initialValue;
    if (value === '' && field.dataset.loading === 'true' && field.dataset.initialValue !== undefined) value = field.dataset.initialValue;
    if (field.hasAttribute('data-dirty-set')) sets.add(field.name);
    (values[field.name] ??= []).push(value);
  }
  for (const name of sets) values[name]?.sort();
  return JSON.stringify(Object.entries(values).sort(([a], [b]) => a.localeCompare(b)));
}

// Editors report the result only after the server has confirmed the write.
export function formSaveResult(form: HTMLFormElement, success: boolean) {
  form.dispatchEvent(new CustomEvent('editor:save-result', { bubbles: true, detail: success }));
}

export async function savePendingForms(forms: HTMLFormElement[]): Promise<boolean> {
  if (!forms.every(form => form.reportValidity())) return false;
  for (const form of forms) {
    if (!form.isConnected) continue;
    form.dataset.savingBeforeLeave = 'true';
    const success = await new Promise<boolean>(resolve => {
      const result = (event: Event) => { form.removeEventListener('editor:save-result', result); resolve((event as CustomEvent<boolean>).detail); };
      const submit = form.querySelector<HTMLButtonElement>('button[type="submit"], button:not([type])');
      if (submit?.disabled) { resolve(false); return; }
      form.addEventListener('editor:save-result', result);
      try { form.requestSubmit(submit ?? undefined); }
      catch { form.removeEventListener('editor:save-result', result); resolve(false); }
    });
    delete form.dataset.savingBeforeLeave;
    if (!success) return false;
    // Allow the owner's busy state to settle before submitting the next edited form.
    await new Promise<void>(resolve => requestAnimationFrame(() => resolve()));
  }
  return true;
}

export function requestEditorClose(event: { currentTarget: HTMLElement }) {
  event.currentTarget.dispatchEvent(new CustomEvent('editor:leave', { bubbles: true }));
}

export function requestEditorAction(element: HTMLElement, action: () => void) {
  element.dispatchEvent(new CustomEvent('editor:leave', { bubbles: true, detail: action }));
}
