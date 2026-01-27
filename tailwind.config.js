/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./app/templates/**/*.html",
        "./app/static/js/**/*.js"
    ],
    theme: {
        extend: {
            colors: {
                slate: {
                    850: '#151e2e',
                    950: '#020617',
                }
            },
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
            },
        },
    },
    plugins: [],
}
