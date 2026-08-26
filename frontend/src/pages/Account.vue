<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { allauth } from "../lib/api";
import { useSession } from "../stores/session";

const session = useSession();
const { t } = useI18n();
const toast = useToast();

const hasPassword = ref<boolean | null>(null);
const currentPassword = ref("");
const newPassword = ref("");
const repeatPassword = ref("");
const error = ref("");
const busy = ref(false);

onMounted(async () => {
  const res = await allauth("GET", "/auth/session");
  hasPassword.value = res.data?.data?.user?.has_usable_password ?? false;
});

async function save() {
  error.value = "";
  if (newPassword.value !== repeatPassword.value) {
    error.value = t("account.passwordMismatch");
    return;
  }
  busy.value = true;
  try {
    const body: Record<string, string> = { new_password: newPassword.value };
    if (hasPassword.value) body.current_password = currentPassword.value;
    const res = await allauth("POST", "/account/password/change", body);
    if (res.status === 200) {
      toast.add({ title: t("account.passwordSaved"), color: "success" });
      hasPassword.value = true;
      currentPassword.value = newPassword.value = repeatPassword.value = "";
    } else {
      error.value = res.data?.errors?.[0]?.message ?? "Something went wrong";
    }
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <main class="mx-auto flex max-w-md flex-col gap-6 px-6 pt-12 pb-10">
    <h1 class="text-xl font-semibold">{{ $t("account.title") }}</h1>

    <UCard>
      <p class="text-sm text-ink-600">{{ $t("auth.emailLabel") }}</p>
      <p class="font-medium">{{ session.me?.email }}</p>
    </UCard>

    <UCard v-if="hasPassword !== null">
      <h2 class="mb-1 font-semibold">{{ $t("account.passwordTitle") }}</h2>
      <p class="mb-4 text-sm text-ink-600">
        {{ hasPassword ? $t("account.hasPasswordHint") : $t("account.noPasswordHint") }}
      </p>
      <form class="flex flex-col gap-3" @submit.prevent="save">
        <UFormField v-if="hasPassword" :label="$t('account.currentPassword')">
          <UInput v-model="currentPassword" type="password" required class="w-full" />
        </UFormField>
        <UFormField :label="$t('account.newPassword')">
          <UInput v-model="newPassword" type="password" required class="w-full" />
        </UFormField>
        <UFormField :label="$t('account.repeatPassword')">
          <UInput v-model="repeatPassword" type="password" required class="w-full" />
        </UFormField>
        <UButton type="submit" :loading="busy" block>
          {{ hasPassword ? $t("account.changePassword") : $t("account.setPassword") }}
        </UButton>
      </form>
      <UAlert v-if="error" color="error" variant="subtle" :description="error" class="mt-3" />
    </UCard>
  </main>
</template>
