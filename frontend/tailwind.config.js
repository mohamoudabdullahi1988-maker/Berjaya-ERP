import preset, { content } from 'frappe-ui/tailwind'

// Brand colours are NOT defined here. They live in src/tokens.css (the single source) and are
// only given Tailwind names below.
const token = (name) => `var(--bj-${name})`

/** @type {import('tailwindcss').Config} */
export default {
  presets: [preset],
  content: ['./index.html', './src/**/*.{vue,js}', ...content],
  theme: {
    extend: {
      colors: {
        bj: {
          charcoal: token('charcoal'),
          ink: token('ink'),
          terracotta: token('terracotta'),
          'terracotta-light': token('terracotta-light'),
          'terracotta-tint': token('terracotta-tint'),
          ground: token('ground'),
          card: token('card'),
          line: token('line'),
          muted: token('muted'),
          completed: token('state-completed'),
          current: token('state-current'),
          blocked: token('state-blocked'),
          pending: token('state-pending'),
        },
      },
      fontFamily: {
        heading: ['"Space Grotesk Variable"', 'system-ui', 'sans-serif'],
        body: ['"Inter Variable"', 'system-ui', 'sans-serif'],
      },
    },
  },
}
