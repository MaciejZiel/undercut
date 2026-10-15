export const driverHref = (slug: string) => `/drivers/${encodeURIComponent(slug)}`;
export const constructorHref = (slug: string) => `/constructors/${encodeURIComponent(slug)}`;
export const circuitHref = (slug: string) => `/circuits/${encodeURIComponent(slug)}`;
export const seasonHref = (year: number) => `/seasons/${year}`;
export const roundHref = (year: number, round: number) => `/seasons/${year}/${round}`;
