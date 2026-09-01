import ui from "@nuxt/ui/vue-plugin";
import { VueQueryPlugin } from "@tanstack/vue-query";
import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import { i18n } from "./i18n";
import "./lib/install";
import { router } from "./router";
import "./style.css";

createApp(App)
  .use(createPinia())
  .use(router)
  .use(i18n)
  .use(ui)
  .use(VueQueryPlugin, {
    queryClientConfig: {
      defaultOptions: {
        queries: { staleTime: 15_000, retry: 1 },
      },
    },
  })
  .mount("#app");
