/**
 * Auto-generated from docs/openapi.json via openapi-typescript.
 * Run `npm run gen:api-types` to regenerate.
 */
export interface paths {
  "/api/v1/auth/whoami": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": {
              user_id: string;
              auth_source: "jwt" | "jwt_cookie" | "cookie";
            };
          };
        };
        401: {
          description: "Unauthorized";
        };
      };
    };
  };
}
