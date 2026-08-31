<script setup lang="ts">
import { ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { allauth, api } from "../lib/api";
import { useSession } from "../stores/session";

const session = useSession();
const { t } = useI18n();
const toast = useToast();

// Opens at most once per page load, and only once a role exists so it never
// covers the onboarding flow. Choosing "keep codes" dismisses it permanently
// (server-side); closing it any other way just postpones it to the next visit.
const open = ref(false);
const shown = ref(false);
watch(
  () => session.me,
  (me) => {
    if (!shown.value && me?.prompt_password_setup && me.role) {
      open.value = true;
      shown.value = true;
    }
  },
  { immediate: true },
);

const showForm = ref(false);
const newPassword = ref("");
const repeatPassword = ref("");
const error = ref("");
const busy = ref(false);

async function setPassword() {
  error.value = "";
  if (newPassword.value !== repeatPassword.value) {
    error.value = t("account.passwordMismatch");
    return;
  }
  busy.value = true;
  try {
    const res = await allauth("POST", "/account/password/change", { new_password: newPassword.value });
    if (res.status === 200) {
      open.value = false;
      toast.add({ title: t("account.passwordSaved"), color: "success" });
      session.refresh();
    } else {
      error.value = res.data?.errors?.[0]?.message ?? "Something went wrong";
    }
  } finally {
    busy.value = false;
  }
}

async function keepCode() {
  open.value = false;
  await api("/me/password-prompt/dismiss", { method: "POST" });
  session.refresh();
}
</script>

<template>
  <UModal v-model:open="open" :title="$t('welcomePrompt.title')">
    <template #body>
      <div class="flex flex-col gap-4">
        <p class="text-sm text-ink-600">{{ $t("welcomePrompt.body") }}</p>
        <form v-if="showForm" class="flex flex-col gap-3" @submit.prevent="setPassword">
          <UFormField :label="$t('account.newPassword')">
            <UInput v-model="newPassword" type="password" required autofocus class="w-full" />
          </UFormField>
          <UFormField :label="$t('account.repeatPassword')">
            <UInput v-model="repeatPassword" type="password" required class="w-full" />
          </UFormField>
          <UButton type="submit" :loading="busy" block>{{ $t("account.setPassword") }}</UButton>
          <UAlert v-if="error" color="error" variant="subtle" :description="error" />
        </form>
        <div v-else class="flex flex-col gap-2">
          <UButton block @click="showForm = true">{{ $t("welcomePrompt.setPassword") }}</UButton>
          <UButton variant="ghost" color="neutral" block @click="keepCode">
            {{ $t("welcomePrompt.keepCode") }}
          </UButton>
        </div>
      </div>
    </template>
  </UModal>
</template>
