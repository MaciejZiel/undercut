/**
 * Nationality (demonym, as stored by the importer) or country name -> ISO 3166-1
 * alpha-2 code -> flag emoji. Unknown values return null: the UI then shows the
 * plain text without a flag.
 */
const NATIONALITY_TO_CODE: Record<string, string> = {
  american: "US",
  argentine: "AR",
  "argentinian": "AR",
  australian: "AU",
  austrian: "AT",
  belgian: "BE",
  brazilian: "BR",
  british: "GB",
  canadian: "CA",
  chilean: "CL",
  chinese: "CN",
  colombian: "CO",
  czech: "CZ",
  danish: "DK",
  dutch: "NL",
  finnish: "FI",
  french: "FR",
  german: "DE",
  hungarian: "HU",
  indian: "IN",
  indonesian: "ID",
  irish: "IE",
  italian: "IT",
  japanese: "JP",
  liechtensteiner: "LI",
  malaysian: "MY",
  mexican: "MX",
  monegasque: "MC",
  "new zealander": "NZ",
  norwegian: "NO",
  polish: "PL",
  portuguese: "PT",
  rhodesian: "ZW",
  russian: "RU",
  "south african": "ZA",
  spanish: "ES",
  swedish: "SE",
  swiss: "CH",
  thai: "TH",
  uruguayan: "UY",
  venezuelan: "VE",
  "east german": "DE",
};

const COUNTRY_TO_CODE: Record<string, string> = {
  argentina: "AR",
  australia: "AU",
  austria: "AT",
  azerbaijan: "AZ",
  bahrain: "BH",
  belgium: "BE",
  brazil: "BR",
  canada: "CA",
  china: "CN",
  france: "FR",
  germany: "DE",
  hungary: "HU",
  india: "IN",
  italy: "IT",
  japan: "JP",
  korea: "KR",
  malaysia: "MY",
  mexico: "MX",
  monaco: "MC",
  morocco: "MA",
  netherlands: "NL",
  portugal: "PT",
  qatar: "QA",
  russia: "RU",
  "saudi arabia": "SA",
  singapore: "SG",
  "south africa": "ZA",
  spain: "ES",
  sweden: "SE",
  switzerland: "CH",
  turkey: "TR",
  uae: "AE",
  "united arab emirates": "AE",
  uk: "GB",
  "united kingdom": "GB",
  usa: "US",
  "united states": "US",
  vietnam: "VN",
};

/** Alphabetical list of nationalities for the filter suggestions. */
export const KNOWN_NATIONALITIES = Object.keys(NATIONALITY_TO_CODE)
  .filter((n) => n !== "east german" && n !== "argentinian")
  .map((n) => n.replace(/\b\w/g, (c) => c.toUpperCase()))
  .sort();

export function codeFor(label: string | null | undefined): string | null {
  if (!label) return null;
  const key = label.trim().toLowerCase();
  return NATIONALITY_TO_CODE[key] ?? COUNTRY_TO_CODE[key] ?? null;
}

export function flagEmoji(code: string): string {
  return [...code.toUpperCase()].map((c) => String.fromCodePoint(0x1f1e6 + c.charCodeAt(0) - 65)).join("");
}

/** Flag emoji for a nationality or country name, or null when it is not known. */
export function flagFor(label: string | null | undefined): string | null {
  const code = codeFor(label);
  return code ? flagEmoji(code) : null;
}
