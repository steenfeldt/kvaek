import { api } from "./api";

export interface CityOption {
  id: number;
  name: string;
  municipality: string;
  label: string;
}

export function searchCities(q: string): Promise<CityOption[]> {
  return api<CityOption[]>(`/cities?q=${encodeURIComponent(q)}`);
}

/** Resolve a free-text name (e.g. from a CVR lookup) to a city. Only an
 * unambiguous exact match counts — the user picks otherwise. */
export async function findCityByName(name: string): Promise<CityOption | null> {
  const exact = (await searchCities(name)).filter((c) => c.name.toLowerCase() === name.trim().toLowerCase());
  return exact.length === 1 ? exact[0] : null;
}

/** Build the picker's selected value from an API profile (name + id). */
export function cityFromProfile(p: { city: string; city_id: number | null }): CityOption | null {
  return p.city_id ? { id: p.city_id, name: p.city, municipality: "", label: p.city } : null;
}
