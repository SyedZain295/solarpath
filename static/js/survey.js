document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('surveyForm');
  const success = document.getElementById('surveySuccess');
  const submitBtn = document.getElementById('surveySubmitBtn');
  const errorBox = document.getElementById('surveyError');

  if (!form) return;

  const surveyType = form.dataset.surveyType || 'homeowner';

  const REQUIRED = {
    homeowner: {
      h1_use_tool: 'survey.val.h1_use_tool',
      h1_biggest_concern: 'survey.val.h1_biggest_concern',
      h1_bill_understanding: 'survey.val.h1_bill_understanding',
      h1_share_info: 'survey.val.h1_share_info',
      h2_property_type: 'survey.val.h2_property_type',
      h2_ownership: 'survey.val.h2_ownership',
      h2_install_timeline: 'survey.val.h2_install_timeline',
      h2_monthly_bill: 'survey.val.h2_monthly_bill',
      h3_outcome_priority: 'survey.val.h3_outcome_priority',
      h3_solar_option: 'survey.val.h3_solar_option',
      h3_compare_quotes: 'survey.val.h3_compare_quotes',
      h4_personal_estimate: 'survey.val.h4_personal_estimate',
      h4_followup_interview: 'survey.val.h4_followup_interview',
    },
    company: {
      s1_monthly_inquiries: 'survey.val.s1_monthly_inquiries',
      s1_weekly_qual_time: 'survey.val.s1_weekly_qual_time',
      s1_loss_stage: 'survey.val.s1_loss_stage',
      s2_time_reduction: 'survey.val.s2_time_reduction',
      s2_quote_ready_value: 'survey.val.s2_quote_ready_value',
      s2_quote_ready_definition: 'survey.val.s2_quote_ready_definition',
      s3_spend_model: 'survey.val.s3_spend_model',
      s3_monthly_spend: 'survey.val.s3_monthly_spend',
      s3_commercial_preference: 'survey.val.s3_commercial_preference',
      s3_followup: 'survey.val.s3_followup',
    },
  };

  const CHECKBOX_GROUPS = {
    homeowner: {
      h2_loads: { min: 1, max: null, label: 'survey.val.h2_loads' },
      h3_trust_supplier: { min: 1, max: null, label: 'survey.val.h3_trust_supplier' },
    },
    company: {
      s1_loss_reasons: { min: 1, max: 3, label: 'survey.val.s1_loss_reasons' },
      s1_info_needed: { min: 1, max: null, label: 'survey.val.s1_info_needed' },
      s2_useful_parts: { min: 1, max: 3, label: 'survey.val.s2_useful_parts' },
      s2_trust_requirements: { min: 1, max: null, label: 'survey.val.s2_trust_requirements' },
      s3_worth_paying: { min: 1, max: 3, label: 'survey.val.s3_worth_paying' },
      s3_stop_using: { min: 1, max: null, label: 'survey.val.s3_stop_using' },
    },
  };

  function labelText(key) {
    return tr(key, key);
  }

  function setupMaxCheckboxes() {
    form.querySelectorAll('.checkbox-group[data-max]').forEach(group => {
      const max = parseInt(group.dataset.max, 10);
      const boxes = group.querySelectorAll('input[type="checkbox"]');
      boxes.forEach(box => {
        box.addEventListener('change', () => {
          const checked = [...boxes].filter(b => b.checked);
          if (checked.length > max) {
            box.checked = false;
            const msg = tr('survey.js.max_options', 'Please select at most {max} options for this question.');
            showError(msg.replace('{max}', max));
          } else {
            clearError();
          }
          boxes.forEach(b => {
            b.disabled = !b.checked && checked.length >= max;
          });
        });
      });
    });
  }

  function setupScaleOutput() {
    const scale = form.querySelector('input[type="range"][name="s2_quote_ready_value"]');
    const out = document.getElementById('scaleValue');
    if (scale && out) {
      scale.addEventListener('input', () => { out.textContent = scale.value; });
    }
  }

  function setupFollowupToggle() {
    const fields = document.getElementById('followupFields');
    if (!fields) return;
    form.querySelectorAll('input[name="s3_followup"]').forEach(radio => {
      radio.addEventListener('change', () => {
        fields.classList.toggle('hidden', radio.value !== 'yes' || !radio.checked);
      });
    });
  }

  function showError(msg) {
    if (!errorBox) { alert(msg); return; }
    errorBox.textContent = msg;
    errorBox.classList.remove('hidden');
    errorBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function clearError() {
    errorBox?.classList.add('hidden');
  }

  function collectData() {
    const fd = new FormData(form);
    const data = { survey_type: surveyType };
    for (const [key, value] of fd.entries()) {
      if (data[key]) {
        if (!Array.isArray(data[key])) data[key] = [data[key]];
        data[key].push(value);
      } else {
        data[key] = value;
      }
    }
    return data;
  }

  function validateCheckboxGroups(data) {
    const groups = CHECKBOX_GROUPS[surveyType] || {};
    for (const [name, rules] of Object.entries(groups)) {
      const values = data[name];
      const count = Array.isArray(values) ? values.length : (values ? 1 : 0);
      const otherKey = `${name}_other`;
      const hasOther = data[otherKey] && String(data[otherKey]).trim();
      if (count < rules.min && !hasOther) {
        const msg = tr('survey.js.answer', 'Please answer: {label}');
        return msg.replace('{label}', labelText(rules.label));
      }
      if (rules.max && count > rules.max) {
        const msg = tr('survey.js.max_for', 'Please select at most {max} for: {label}');
        return msg.replace('{max}', rules.max).replace('{label}', labelText(rules.label));
      }
    }
    return null;
  }

  function validate(data) {
    const required = REQUIRED[surveyType] || REQUIRED.homeowner;
    for (const [key, labelKey] of Object.entries(required)) {
      if (!data[key] || data[key] === '') {
        const msg = tr('survey.js.answer', 'Please answer: {label}');
        return msg.replace('{label}', labelText(labelKey));
      }
    }

    const checkboxError = validateCheckboxGroups(data);
    if (checkboxError) return checkboxError;

    if (surveyType === 'company' && data.s3_followup === 'yes') {
      if (!data.s3_followup_company?.trim()) return tr('survey.js.company_name_required', 'Please enter your company name for follow-up.');
      if (!data.s3_followup_email?.trim()) return tr('survey.js.email_required', 'Please enter your email for follow-up.');
    }

    if (surveyType === 'homeowner') {
      if (data.h1_biggest_concern === 'other' && !data.h1_biggest_concern_other?.trim()) {
        return tr('survey.js.concern_required', 'Please specify your biggest concern.');
      }
      if (data.h2_property_type === 'other' && !data.h2_property_type_other?.trim()) {
        return tr('survey.js.property_required', 'Please specify your property type.');
      }
    }

    return null;
  }

  function showSuccess(data) {
    form.classList.add('hidden');
    success.classList.remove('hidden');
    success.scrollIntoView({ behavior: 'smooth', block: 'start' });
    localStorage.setItem(`solarSurvey_${surveyType}`, JSON.stringify({ ...data, submitted_at: new Date().toISOString() }));
  }

  setupMaxCheckboxes();
  setupScaleOutput();
  setupFollowupToggle();

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();

    const data = collectData();
    const validationError = validate(data);
    if (validationError) {
      showError(validationError);
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = tr('survey.js.submitting', 'Submitting...');

    try {
      const resp = await fetch('/api/survey', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      const body = await resp.json().catch(() => ({}));

      if (resp.ok) {
        showSuccess(data);
        return;
      }

      if (resp.status >= 400 && resp.status < 500) {
        throw new Error(body.error || tr('survey.js.check_answers', 'Please check your answers and try again.'));
      }

      const errMsg = tr('survey.js.server_error', 'Server error ({status})');
      throw new Error(body.error || errMsg.replace('{status}', resp.status));
    } catch (err) {
      if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        showSuccess(data);
        const note = document.getElementById('surveySuccessNote');
        if (note) {
          note.textContent = tr('survey.js.offline_note', 'Saved on this device — server was unreachable.');
          note.classList.remove('hidden');
        }
        return;
      }
      showError(err.message || tr('survey.js.submit_fail', 'Could not submit survey. Please try again.'));
      submitBtn.disabled = false;
      submitBtn.textContent = surveyType === 'company'
        ? tr('survey.c.submit', 'Submit company survey')
        : tr('survey.h.submit', 'Submit homeowner survey');
    }
  });
});
