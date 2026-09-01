import { ref } from "vue";

// Chromium fires beforeinstallprompt once, shortly after page load — long
// before any page component mounts. Capture it here at module scope; main.ts
// imports this module so the listener exists from startup.
export const installPrompt = ref<(Event & { prompt: () => Promise<void> }) | null>(null);

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  installPrompt.value = e as Event & { prompt: () => Promise<void> };
});
