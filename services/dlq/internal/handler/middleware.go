package handler

import (
	"net/http"
	"strings"

	"github.com/golang-jwt/jwt/v5"
)

// JWTAuth validates the bearer token using the shared JWT secret. It is a thin
// re-implementation of the audit service middleware so the DLQ worker stays a
// self-contained service (no shared internal package import across services).
func JWTAuth(secret string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			auth := r.Header.Get("Authorization")
			if !strings.HasPrefix(auth, "Bearer ") {
				writeError(w, http.StatusUnauthorized, "UNAUTHORIZED", "missing or malformed authorization header")
				return
			}
			tokenStr := strings.TrimPrefix(auth, "Bearer ")
			claims := jwt.MapClaims{}
			_, err := jwt.ParseWithClaims(tokenStr, claims, func(t *jwt.Token) (any, error) {
				if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
					return nil, jwt.ErrSignatureInvalid
				}
				return []byte(secret), nil
			})
			if err != nil {
				writeError(w, http.StatusUnauthorized, "UNAUTHORIZED", "invalid or expired token")
				return
			}
			ctx := withClaims(r.Context(), claims)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// RequireRole ensures the authenticated principal carries one of the allowed
// roles. Roles are read from the "roles" array claim set by the Auth Service.
func RequireRole(secret string, allowed ...string) func(http.Handler) http.Handler {
	allowedSet := make(map[string]struct{}, len(allowed))
	for _, r := range allowed {
		allowedSet[r] = struct{}{}
	}
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			claims, ok := claimsFrom(r.Context())
			if !ok {
				writeError(w, http.StatusUnauthorized, "UNAUTHORIZED", "missing authentication context")
				return
			}
			raw, _ := claims["roles"].([]interface{})
			okRole := false
			for _, item := range raw {
				if s, ok := item.(string); ok {
					if _, ok := allowedSet[s]; ok {
						okRole = true
						break
					}
				}
			}
			if !okRole {
				writeError(w, http.StatusForbidden, "FORBIDDEN", "insufficient role")
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}
