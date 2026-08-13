/** Map Flask / classic URLs onto React Router paths under basename `/app`. */
export function toSpaPath(raw: string | null | undefined): string {
  const value = (raw || "/").trim() || "/";
  if (value === "/app" || value === "/app/") {
    return "/";
  }
  if (value.startsWith("/app/")) {
    const rest = value.slice(4);
    return rest.startsWith("/") ? rest : `/${rest}`;
  }
  return value.startsWith("/") ? value : `/${value}`;
}
