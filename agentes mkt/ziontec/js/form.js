// ============================================
// ZIONTEC — Contact Form Handler
// ============================================

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('assessmentForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const submitBtn = document.getElementById('submitBtn');
    const successAlert = document.getElementById('successAlert');
    const errorAlert = document.getElementById('errorAlert');

    // Hide previous alerts
    successAlert.style.display = 'none';
    errorAlert.style.display = 'none';

    // Validate required fields
    const required = ['firstName', 'lastName', 'email', 'phone', 'address', 'state', 'propertyType', 'services'];
    let valid = true;

    required.forEach(id => {
      const field = document.getElementById(id);
      if (!field.value.trim()) {
        field.style.borderColor = '#EF4444';
        valid = false;
      } else {
        field.style.borderColor = '';
      }
    });

    // Email format validation
    const emailField = document.getElementById('email');
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(emailField.value)) {
      emailField.style.borderColor = '#EF4444';
      valid = false;
    }

    if (!valid) {
      errorAlert.textContent = '⚠ Please fill in all required fields correctly.';
      errorAlert.style.display = 'block';
      errorAlert.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    // Loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';

    // Collect form data
    const formData = new FormData(form);

    try {
      const response = await fetch('php/form-handler.php', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (result.success) {
        successAlert.style.display = 'block';
        form.reset();
        successAlert.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else {
        throw new Error(result.message || 'Server error');
      }
    } catch (err) {
      errorAlert.style.display = 'block';
      errorAlert.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fa-solid fa-calendar-check"></i> Schedule My Free Assessment';
    }
  });

  // Clear red border on input
  document.querySelectorAll('.form-control').forEach(field => {
    field.addEventListener('input', () => {
      field.style.borderColor = '';
    });
  });
});
