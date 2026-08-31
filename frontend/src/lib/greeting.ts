import { computed } from "vue";
import { useI18n } from "vue-i18n";

/** Shared dashboard header bits: localized "today" and time-of-day greeting. */
export function useGreeting() {
  const { t, locale } = useI18n();
  const today = computed(() =>
    new Date().toLocaleDateString(locale.value === "da" ? "da-DK" : "en-GB", {
      weekday: "long",
      day: "numeric",
      month: "long",
    }),
  );
  const greeting = computed(() => {
    const h = new Date().getHours();
    if (h < 5 || h >= 18) return t("dashboard.evening");
    if (h < 12) return t("dashboard.morning");
    return t("dashboard.afternoon");
  });
  return { today, greeting };
}
