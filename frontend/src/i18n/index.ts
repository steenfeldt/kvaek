import { createI18n } from "vue-i18n";
import da from "./da.json";
import en from "./en.json";

export const i18n = createI18n({
  legacy: false,
  locale: "da",
  fallbackLocale: "en",
  messages: { da, en },
});
