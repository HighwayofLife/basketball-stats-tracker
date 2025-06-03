/**
 * CRUD Module - Reusable Create, Read, Update, Delete operations
 * Provides common patterns for managing entities with forms and tables
 */

class CrudManager {
    constructor(entityName, apiClient, options = {}) {
        this.entityName = entityName;
        this.apiClient = apiClient;
        this.options = {
            tableId: `${entityName}-table`,
            modalId: `${entityName}-modal`,
            formId: `${entityName}-form`,
            createMethod: 'create' + this.capitalize(entityName),
            updateMethod: 'update' + this.capitalize(entityName),
            deleteMethod: 'delete' + this.capitalize(entityName),
            listMethod: 'get' + this.capitalize(entityName) + 's',
            ...options
        };
        
        this.currentEntity = null;
        this.isEditing = false;
    }

    /**
     * Capitalize first letter of string
     * @param {string} str 
     * @returns {string}
     */
    capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    /**
     * Initialize CRUD functionality
     */
    init() {
        this.loadEntities();
        this.setupEventListeners();
    }

    /**
     * Load and display entities
     * @param {Object} filters - Optional filters
     */
    async loadEntities(filters = {}) {
        try {
            this.showTableLoading();
            const entities = await this.apiClient[this.options.listMethod](filters);
            this.renderEntitiesTable(entities);
        } catch (error) {
            this.showTableError(error.message);
            console.error(`Error loading ${this.entityName}s:`, error);
        }
    }

    /**
     * Show loading state in table
     */
    showTableLoading() {
        const tableBody = document.querySelector(`#${this.options.tableId}-body`);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr class="loading-row">
                    <td colspan="100%" class="text-center p-4">
                        <div class="spinner-border text-primary me-2" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        Loading ${this.entityName}s...
                    </td>
                </tr>
            `;
        }
    }

    /**
     * Show error state in table
     * @param {string} message 
     */
    showTableError(message) {
        const tableBody = document.querySelector(`#${this.options.tableId}-body`);
        if (tableBody) {
            tableBody.innerHTML = `
                <tr class="error-row">
                    <td colspan="100%" class="text-center p-4 text-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Error loading ${this.entityName}s: ${message}
                        <br>
                        <button class="btn btn-sm btn-outline-primary mt-2" id="${this.options.tableId}-retry-button">
                            <i class="fas fa-refresh"></i> Try Again
                        </button>
                    </td>
                </tr>
            `;
            
            // Properly bind the retry button event listener
            const retryButton = document.querySelector(`#${this.options.tableId}-retry-button`);
            if (retryButton) {
                retryButton.addEventListener('click', () => this.loadEntities());
            }
        }
    }

    /**
     * Render entities in table - should be overridden by subclasses
     * @param {Array} entities 
     */
    renderEntitiesTable(entities) {
        console.warn('renderEntitiesTable should be implemented by subclass');
    }

    /**
     * Setup event listeners for CRUD operations
     */
    setupEventListeners() {
        // Add button
        const addBtn = document.querySelector(`[data-action="add-${this.entityName}"]`);
        if (addBtn) {
            addBtn.addEventListener('click', () => this.showCreateModal());
        }

        // Form submission
        const form = document.getElementById(this.options.formId);
        if (form) {
            form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Modal reset on close
        const modal = document.getElementById(this.options.modalId);
        if (modal) {
            modal.addEventListener('hidden.bs.modal', () => this.resetForm());
        }
    }

    /**
     * Show create modal
     */
    showCreateModal() {
        this.isEditing = false;
        this.currentEntity = null;
        this.resetForm();
        this.updateModalTitle(`Add New ${this.capitalize(this.entityName)}`);
        this.showModal();
    }

    /**
     * Show edit modal
     * @param {Object} entity 
     */
    showEditModal(entity) {
        this.isEditing = true;
        this.currentEntity = entity;
        this.populateForm(entity);
        this.updateModalTitle(`Edit ${this.capitalize(this.entityName)}`);
        this.showModal();
    }

    /**
     * Show modal
     */
    showModal() {
        const modal = new bootstrap.Modal(document.getElementById(this.options.modalId));
        modal.show();
    }

    /**
     * Hide modal
     */
    hideModal() {
        const modal = bootstrap.Modal.getInstance(document.getElementById(this.options.modalId));
        if (modal) {
            modal.hide();
        }
    }

    /**
     * Update modal title
     * @param {string} title 
     */
    updateModalTitle(title) {
        const titleElement = document.querySelector(`#${this.options.modalId} .modal-title`);
        if (titleElement) {
            titleElement.textContent = title;
        }
    }

    /**
     * Reset form to initial state
     */
    resetForm() {
        const form = document.getElementById(this.options.formId);
        if (form) {
            form.reset();
            this.clearValidationErrors();
        }
    }

    /**
     * Populate form with entity data - should be overridden by subclasses
     * @param {Object} entity 
     */
    populateForm(entity) {
        console.warn('populateForm should be implemented by subclass');
    }

    /**
     * Get form data - should be overridden by subclasses
     * @returns {Object}
     */
    getFormData() {
        console.warn('getFormData should be implemented by subclass');
        return {};
    }

    /**
     * Handle form submission
     * @param {Event} event 
     */
    async handleFormSubmit(event) {
        event.preventDefault();
        
        try {
            this.clearValidationErrors();
            const formData = this.getFormData();
            
            if (this.isEditing) {
                await this.updateEntity(this.currentEntity.id, formData);
            } else {
                await this.createEntity(formData);
            }
            
            this.hideModal();
            this.loadEntities();
            this.showSuccessMessage(
                this.isEditing 
                    ? `${this.capitalize(this.entityName)} updated successfully!`
                    : `${this.capitalize(this.entityName)} created successfully!`
            );
        } catch (error) {
            this.handleFormError(error);
        }
    }

    /**
     * Create entity
     * @param {Object} data 
     */
    async createEntity(data) {
        return await this.apiClient[this.options.createMethod](data);
    }

    /**
     * Update entity
     * @param {number} id 
     * @param {Object} data 
     */
    async updateEntity(id, data) {
        return await this.apiClient[this.options.updateMethod](id, data);
    }

    /**
     * Delete entity with confirmation
     * @param {number} id 
     * @param {string} name 
     */
    async deleteEntity(id, name) {
        if (!confirm(`Are you sure you want to delete ${name}? This action cannot be undone.`)) {
            return;
        }

        try {
            await this.apiClient[this.options.deleteMethod](id);
            this.loadEntities();
            this.showSuccessMessage(`${this.capitalize(this.entityName)} deleted successfully!`);
        } catch (error) {
            this.showErrorMessage(`Error deleting ${this.entityName}: ${error.message}`);
        }
    }

    /**
     * Handle form validation errors
     * @param {Error} error 
     */
    handleFormError(error) {
        if (error.isValidationError && error.data.errors) {
            this.showValidationErrors(error.data.errors);
        } else {
            this.showErrorMessage(`Error saving ${this.entityName}: ${error.message}`);
        }
    }

    /**
     * Show validation errors on form fields
     * @param {Object} errors 
     */
    showValidationErrors(errors) {
        Object.keys(errors).forEach(field => {
            const input = document.querySelector(`#${this.options.formId} [name="${field}"]`);
            if (input) {
                input.classList.add('is-invalid');
                
                // Add error message
                let errorDiv = input.parentNode.querySelector('.invalid-feedback');
                if (!errorDiv) {
                    errorDiv = document.createElement('div');
                    errorDiv.className = 'invalid-feedback';
                    input.parentNode.appendChild(errorDiv);
                }
                errorDiv.textContent = errors[field];
            }
        });
    }

    /**
     * Clear validation errors
     */
    clearValidationErrors() {
        const form = document.getElementById(this.options.formId);
        if (form) {
            form.querySelectorAll('.is-invalid').forEach(input => {
                input.classList.remove('is-invalid');
            });
            form.querySelectorAll('.invalid-feedback').forEach(error => {
                error.remove();
            });
        }
    }

    /**
     * Show success message
     * @param {string} message 
     */
    showSuccessMessage(message) {
        this.showAlert(message, 'success');
    }

    /**
     * Show error message
     * @param {string} message 
     */
    showErrorMessage(message) {
        this.showAlert(message, 'danger');
    }

    /**
     * Show alert message
     * @param {string} message 
     * @param {string} type 
     */
    showAlert(message, type = 'info') {
        // Remove existing alerts
        document.querySelectorAll('.crud-alert').forEach(alert => alert.remove());
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show crud-alert`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insert at top of main content
        const container = document.querySelector('.site-content .container');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
        }
        
        // Auto-dismiss after 5 seconds for success/info
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                alertDiv.remove();
            }, 5000);
        }
    }
}

// Export for use in other modules
window.CrudManager = CrudManager;