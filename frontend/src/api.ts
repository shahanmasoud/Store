export type User = {
  id: number | string;
  username: string;
  full_name?: string | null;
  is_active?: boolean;
  is_superuser?: boolean;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("store_auth_token");
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");

  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = "ارتباط با سرور برقرار نشد. دوباره تلاش کنید.";
    try {
      const body = await response.json();
      message = body.detail ?? body.message ?? message;
    } catch {
      message =
        response.status === 401 ? "نام کاربری یا رمز عبور درست نیست." : message;
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export const api = {
  login(username: string, password: string) {
    return request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },
  me() {
    return request<User>("/auth/me");
  },
};
