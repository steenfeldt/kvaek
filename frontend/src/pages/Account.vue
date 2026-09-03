<script setup lang="ts">
import { useMutation, useQuery, useQueryClient } from "@tanstack/vue-query";
import { onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import CityPicker from "../components/CityPicker.vue";
import InstallApp from "../components/InstallApp.vue";
import { allauth, api } from "../lib/api";
import { cityFromProfile, findCityByName, type CityOption } from "../lib/cities";
import { useSession } from "../stores/session";

interface Brand {
  company_name: string;
  cvr: string;
  website: string;
  city: string;
  city_id: number | null;
}

const session = useSession();
const { t } = useI18n();
const toast = useToast();
const queryClient = useQueryClient();

const isBrand = session.role === "brand";
const { data: brand } = useQuery({
  queryKey: ["my-brand"],
  queryFn: () => api<Brand>("/me/brand"),
  enabled: isBrand,
});
const brandForm = ref({ company_name: "", cvr: "", website: "" });
const brandCity = ref<CityOption | null>(null);
watch(
  brand,
  (b) => {
    if (!b) return;
    brandForm.value = { company_name: b.company_name, cvr: b.cvr, website: b.website };
    brandCity.value = cityFromProfile(b);
  },
  { immediate: true },
);

const brandMutation = useMutation({
  mutationFn: () =>
    api<Brand>("/me/brand", {
      method: "PATCH",
      body: JSON.stringify({ ...brandForm.value, city_id: brandCity.value?.id ?? null }),
    }),
  onSuccess: (data) => {
    queryClient.setQueryData(["my-brand"], data);
    session.refresh();
    toast.add({ title: t("account.companySaved"), color: "success" });
  },
  onError: (e) => toast.add({ title: e.message, color: "error" }),
});

async function cvrLookup() {
  if (!/^\d{8}$/.test(brandForm.value.cvr)) return;
  try {
    const res = await fetch(`https://cvrapi.dk/api?country=dk&vat=${brandForm.value.cvr}`);
    if (res.ok) {
      const data = await res.json();
      if (data.name) brandForm.value.company_name = data.name;
      if (data.city) brandCity.value = await findCityByName(data.city);
    }
  } catch {}
}

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

    <UCard v-if="isBrand && brand">
      <h2 class="mb-3 font-semibold">{{ $t("account.companyTitle") }}</h2>
      <form class="flex flex-col gap-3" @submit.prevent="brandMutation.mutate()">
        <UFormField :label="$t('onboarding.cvr')" required>
          <div class="flex gap-2">
            <UInput v-model="brandForm.cvr" maxlength="8" required pattern="\d{8}" class="flex-1" @blur="cvrLookup" />
            <UButton variant="outline" color="neutral" @click="cvrLookup">{{ $t("onboarding.cvrLookup") }}</UButton>
          </div>
        </UFormField>
        <UFormField :label="$t('onboarding.companyName')" required>
          <UInput v-model="brandForm.company_name" required class="w-full" />
        </UFormField>
        <UFormField :label="$t('onboarding.website')">
          <UInput v-model="brandForm.website" type="url" class="w-full" />
        </UFormField>
        <UFormField :label="$t('onboarding.city')">
          <CityPicker v-model="brandCity" />
        </UFormField>
        <UButton type="submit" :loading="brandMutation.isPending.value" block>
          {{ $t("profile.save") }}
        </UButton>
      </form>
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

    <InstallApp />
  </main>
</template>
