export default (config = {}) => ({
    options: config.options || [],
    value: config.value || '',
    search: '',
    open: false,
    placeholder: config.placeholder || 'Seleccionar...',

    get selectedLabel() {
        const option = this.options.find(o => o.value == this.value);
        return option ? option.label : (this.value || this.placeholder);
    },

    get filteredOptions() {
        if (!this.search) return this.options;
        return this.options.filter(o =>
            o.label.toLowerCase().includes(this.search.toLowerCase())
        );
    },

    toggle() {
        if (this.open) return this.close();
        this.open = true;
    },

    close() {
        this.open = false;
        this.search = '';
    },

    select(val) {
        this.value = val;
        this.close();
        this.$dispatch('change', val);
    },

    clickOutside() {
        this.close();
    }
});
