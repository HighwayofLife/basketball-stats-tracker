/**
 * Validation Module - Form validation utilities
 * Provides reusable validation patterns and functions
 */

class FormValidator {
    constructor(formElement, rules = {}) {
        this.form = formElement;
        this.rules = rules;
        this.errors = {};
        this.isValid = true;
    }

    /**
     * Add validation rule for a field
     * @param {string} fieldName 
     * @param {Array} rules 
     */
    addRule(fieldName, rules) {
        this.rules[fieldName] = rules;
    }

    /**
     * Validate all fields
     * @returns {boolean}
     */
    validate() {
        this.errors = {};
        this.isValid = true;

        Object.keys(this.rules).forEach(fieldName => {
            const field = this.form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                this.validateField(fieldName, field.value);
            }
        });

        this.displayErrors();
        return this.isValid;
    }

    /**
     * Validate a single field
     * @param {string} fieldName 
     * @param {*} value 
     */
    validateField(fieldName, value) {
        const rules = this.rules[fieldName];
        const fieldErrors = [];

        rules.forEach(rule => {
            const result = this.applyRule(rule, value, fieldName);
            if (result !== true) {
                fieldErrors.push(result);
            }
        });

        if (fieldErrors.length > 0) {
            this.errors[fieldName] = fieldErrors[0]; // Show first error
            this.isValid = false;
        }
    }

    /**
     * Apply a validation rule
     * @param {Object|Function} rule 
     * @param {*} value 
     * @param {string} fieldName 
     * @returns {boolean|string}
     */
    applyRule(rule, value, fieldName) {
        if (typeof rule === 'function') {
            return rule(value, fieldName);
        }

        const { type, message, ...params } = rule;

        switch (type) {
            case 'required':
                return ValidationRules.required(value) || message || `${fieldName} is required`;
            
            case 'email':
                return ValidationRules.email(value) || message || 'Please enter a valid email address';
            
            case 'min':
                return ValidationRules.min(value, params.value) || message || `Minimum value is ${params.value}`;
            
            case 'max':
                return ValidationRules.max(value, params.value) || message || `Maximum value is ${params.value}`;
            
            case 'minLength':
                return ValidationRules.minLength(value, params.length) || message || `Minimum length is ${params.length} characters`;
            
            case 'maxLength':
                return ValidationRules.maxLength(value, params.length) || message || `Maximum length is ${params.length} characters`;
            
            case 'pattern':
                return ValidationRules.pattern(value, params.regex) || message || 'Invalid format';
            
            case 'numeric':
                return ValidationRules.numeric(value) || message || 'Please enter a valid number';
            
            case 'integer':
                return ValidationRules.integer(value) || message || 'Please enter a whole number';
            
            case 'positive':
                return ValidationRules.positive(value) || message || 'Please enter a positive number';
            
            case 'jerseyNumber':
                return ValidationRules.jerseyNumber(value) || message || 'Jersey number must be between 0 and 99';
            
            case 'height':
                return ValidationRules.height(value) || message || 'Please enter height in format like 6\'2" or 6-2';
            
            default:
                console.warn(`Unknown validation rule: ${type}`);
                return true;
        }
    }

    /**
     * Display validation errors in the form
     */
    displayErrors() {
        // Clear existing errors
        this.clearErrors();

        Object.keys(this.errors).forEach(fieldName => {
            const field = this.form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.classList.add('is-invalid');
                
                // Add error message
                const errorDiv = document.createElement('div');
                errorDiv.className = 'invalid-feedback';
                errorDiv.textContent = this.errors[fieldName];
                field.parentNode.appendChild(errorDiv);
            }
        });
    }

    /**
     * Clear all validation errors
     */
    clearErrors() {
        this.form.querySelectorAll('.is-invalid').forEach(field => {
            field.classList.remove('is-invalid');
        });
        
        this.form.querySelectorAll('.invalid-feedback').forEach(errorDiv => {
            errorDiv.remove();
        });
    }

    /**
     * Setup real-time validation
     */
    setupRealTimeValidation() {
        Object.keys(this.rules).forEach(fieldName => {
            const field = this.form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.addEventListener('blur', () => {
                    this.validateField(fieldName, field.value);
                    this.displayFieldError(fieldName);
                });

                field.addEventListener('input', () => {
                    if (field.classList.contains('is-invalid')) {
                        this.validateField(fieldName, field.value);
                        this.displayFieldError(fieldName);
                    }
                });
            }
        });
    }

    /**
     * Display error for a specific field
     * @param {string} fieldName 
     */
    displayFieldError(fieldName) {
        const field = this.form.querySelector(`[name="${fieldName}"]`);
        if (!field) return;

        // Clear existing error for this field
        field.classList.remove('is-invalid');
        const existingError = field.parentNode.querySelector('.invalid-feedback');
        if (existingError) {
            existingError.remove();
        }

        // Show new error if exists
        if (this.errors[fieldName]) {
            field.classList.add('is-invalid');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            errorDiv.textContent = this.errors[fieldName];
            field.parentNode.appendChild(errorDiv);
        }
    }
}

/**
 * Common validation rules
 */
class ValidationRules {
    static required(value) {
        if (value === null || value === undefined) return false;
        if (typeof value === 'string') return value.trim().length > 0;
        if (Array.isArray(value)) return value.length > 0;
        return true;
    }

    static email(value) {
        if (!value) return true; // Optional field
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(value);
    }

    static min(value, min) {
        if (!value) return true; // Optional field
        return Number(value) >= min;
    }

    static max(value, max) {
        if (!value) return true; // Optional field
        return Number(value) <= max;
    }

    static minLength(value, length) {
        if (!value) return true; // Optional field
        return value.length >= length;
    }

    static maxLength(value, length) {
        if (!value) return true; // Optional field
        return value.length <= length;
    }

    static pattern(value, regex) {
        if (!value) return true; // Optional field
        return regex.test(value);
    }

    static numeric(value) {
        if (!value) return true; // Optional field
        return !isNaN(value) && !isNaN(parseFloat(value));
    }

    static integer(value) {
        if (!value) return true; // Optional field
        return Number.isInteger(Number(value));
    }

    static positive(value) {
        if (!value) return true; // Optional field
        return Number(value) > 0;
    }

    static jerseyNumber(value) {
        if (!value) return false; // Required field
        const num = Number(value);
        return Number.isInteger(num) && num >= 0 && num <= 99;
    }

    static height(value) {
        if (!value) return true; // Optional field
        // Accept formats like: 6'2", 6-2, 6'2, 6 2, 72 (inches only)
        const heightRegex = /^(\d+)[''\-\s]?(\d+)?"?$|^\d+$/;
        return heightRegex.test(value.trim());
    }

    static weight(value) {
        if (!value) return true; // Optional field
        const num = Number(value);
        return !isNaN(num) && num > 0 && num <= 500; // Reasonable weight range
    }

    static phoneNumber(value) {
        if (!value) return true; // Optional field
        // Accept various phone number formats
        const phoneRegex = /^[\+]?[\d\s\-\(\)\.]{10,}$/;
        return phoneRegex.test(value);
    }

    static url(value) {
        if (!value) return true; // Optional field
        try {
            new URL(value);
            return true;
        } catch {
            return false;
        }
    }

    static dateRange(value, minDate, maxDate) {
        if (!value) return true; // Optional field
        const date = new Date(value);
        const min = new Date(minDate);
        const max = new Date(maxDate);
        return date >= min && date <= max;
    }

    static uniqueInArray(value, array, excludeIndex = -1) {
        return !array.some((item, index) => 
            index !== excludeIndex && item === value
        );
    }
}

/**
 * Pre-defined validation rule sets for common entities
 */
const ValidationPresets = {
    player: {
        name: [
            { type: 'required' },
            { type: 'minLength', length: 2, message: 'Name must be at least 2 characters' },
            { type: 'maxLength', length: 100, message: 'Name cannot exceed 100 characters' }
        ],
        jersey_number: [
            { type: 'required' },
            { type: 'jerseyNumber' }
        ],
        height: [
            { type: 'height' }
        ],
        weight: [
            { type: 'weight' }
        ],
        email: [
            { type: 'email' }
        ]
    },

    team: {
        name: [
            { type: 'required' },
            { type: 'minLength', length: 2, message: 'Team name must be at least 2 characters' },
            { type: 'maxLength', length: 100, message: 'Team name cannot exceed 100 characters' }
        ],
        display_name: [
            { type: 'maxLength', length: 50, message: 'Display name cannot exceed 50 characters' }
        ]
    },

    game: {
        date: [
            { type: 'required' }
        ],
        home_team_id: [
            { type: 'required', message: 'Please select a home team' }
        ],
        away_team_id: [
            { type: 'required', message: 'Please select an away team' }
        ]
    }
};

// Utility function to create validator with preset rules
function createValidator(formElement, entityType, additionalRules = {}) {
    const rules = { ...ValidationPresets[entityType], ...additionalRules };
    return new FormValidator(formElement, rules);
}

// Export for use in other modules
window.FormValidator = FormValidator;
window.ValidationRules = ValidationRules;
window.ValidationPresets = ValidationPresets;
window.createValidator = createValidator;