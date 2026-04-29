# REACT_MIGRATION.md — Streamlit → React

> Guia de migração do frontend. Atualizar checklist conforme itens forem concluídos.

---

## Quando migrar

Migrar quando o Streamlit virar gargalo de UX — mobile-first, customização total, SaaS profissional.
Enquanto isso, Streamlit serve bem para dashboard interno.

---

## Stack

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@tanstack/react-query": "^5.14.0",
    "axios": "^1.6.2",
    "recharts": "^2.10.3",
    "@headlessui/react": "^1.7.17",
    "@heroicons/react": "^2.1.1",
    "tailwindcss": "^3.3.6",
    "zustand": "^4.4.7"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.3",
    "vite": "^5.0.7",
    "vitest": "^1.0.0",
    "@testing-library/react": "^14.0.0"
  }
}
```

---

## Estrutura de pastas

```
frontend-react/
├── src/
│   ├── components/
│   │   ├── Auth/
│   │   │   ├── Login.tsx
│   │   │   └── Register.tsx
│   │   ├── Dashboard/
│   │   │   ├── MetricsCard.tsx
│   │   │   ├── RevenueChart.tsx
│   │   │   ├── AnunciosChart.tsx      ← a implementar
│   │   │   └── PeriodMetrics.tsx
│   │   ├── Upload/
│   │   │   ├── FileUploader.tsx       ← drag-and-drop + barra de progresso
│   │   │   └── UploadHistory.tsx
│   │   └── Layout/
│   │       ├── Sidebar.tsx
│   │       ├── Header.tsx
│   │       └── Footer.tsx
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── AnunciosPage.tsx           ← a implementar
│   │   ├── UploadPage.tsx
│   │   └── HistoryPage.tsx
│   ├── services/
│   │   └── api.ts                     ← Axios client com interceptors JWT
│   ├── hooks/
│   │   ├── useAuth.ts                 ← Zustand
│   │   ├── useUpload.ts
│   │   ├── useDashboard.ts            ← React Query
│   │   └── useAnuncios.ts             ← a implementar
│   ├── types/
│   │   └── index.ts
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── tsconfig.json
├── vite.config.ts
└── Dockerfile
```

---

## Serviço de API (`src/services/api.ts`)

Axios com interceptors para JWT e redirect automático no 401.

```typescript
import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

class APIClient {
  private client: AxiosInstance;
  private token: string | null = localStorage.getItem('token');

  constructor() {
    this.client = axios.create({ baseURL: API_BASE_URL });

    this.client.interceptors.request.use((config) => {
      if (this.token) config.headers.Authorization = `Bearer ${this.token}`;
      return config;
    });

    this.client.interceptors.response.use(
      (res) => res,
      (err) => {
        if (err.response?.status === 401) {
          this.token = null;
          window.location.href = '/login';
        }
        return Promise.reject(err);
      }
    );
  }

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('token', token);
  }

  // Auth
  async login(username: string, password: string) {
    const res = await this.client.post('/auth/login', { username, password });
    this.setToken(res.data.access_token);
    return res.data;
  }
  async register(email: string, username: string, password: string) {
    return (await this.client.post('/auth/register', { email, username, password })).data;
  }

  // Upload
  async uploadFaturamento(file: File, onProgress?: (p: number) => void) {
    return this._upload('/upload/faturamento', file, onProgress);
  }
  async uploadAnuncios(file: File, onProgress?: (p: number) => void) {
    return this._upload('/upload/anuncios', file, onProgress);
  }
  private async _upload(route: string, file: File, onProgress?: (p: number) => void) {
    const fd = new FormData();
    fd.append('file', file);
    const res = await this.client.post(route, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total) onProgress?.(Math.round((e.loaded * 100) / e.total));
      },
    });
    return res.data;
  }

  // Dashboard
  async getDashboard()  { return (await this.client.get('/dashboard/')).data; }
  async getAnuncios()   { return (await this.client.get('/dashboard/anuncios')).data; }
  async listUploads()   { return (await this.client.get('/upload/')).data; }
  async deleteUpload(id: number) { await this.client.delete(`/upload/${id}`); }
}

export const apiClient = new APIClient();
```

---

## Hooks principais

### `useAuth.ts` — Zustand

```typescript
import { create } from 'zustand';
import { apiClient } from '@/services/api';

interface AuthState {
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  isAuthenticated: !!localStorage.getItem('token'),

  login: async (username, password) => {
    await apiClient.login(username, password);
    set({ isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ isAuthenticated: false });
    window.location.href = '/login';
  },
}));
```

### `useDashboard.ts` — React Query

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

export const useDashboard = () =>
  useQuery({
    queryKey: ['dashboard'],
    queryFn: () => apiClient.getDashboard(),
    staleTime: 5 * 60 * 1000,
  });

export const useAnuncios = () =>
  useQuery({
    queryKey: ['anuncios'],
    queryFn: () => apiClient.getAnuncios(),
    staleTime: 5 * 60 * 1000,
  });
```

---

## Componentes principais

### `MetricsCard.tsx`

```tsx
interface MetricCardProps {
  title: string;
  value: number;
  format?: 'currency' | 'number' | 'percent';
  delta?: number;
}

export function MetricCard({ title, value, format = 'number', delta }: MetricCardProps) {
  const fmt = (v: number) => {
    if (format === 'currency')
      return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(v);
    if (format === 'percent') return `${v.toFixed(2)}%`;
    return v.toLocaleString('pt-BR');
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-gray-500 text-sm font-medium">{title}</h3>
      <p className="text-3xl font-bold mt-2">{fmt(value)}</p>
      {delta !== undefined && (
        <p className={`text-sm mt-2 ${delta >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          {delta >= 0 ? '↑' : '↓'} {Math.abs(delta).toFixed(1)}%
        </p>
      )}
    </div>
  );
}
```

### `FileUploader.tsx` — drag-and-drop

```tsx
import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { apiClient } from '@/services/api';

interface Props { type: 'faturamento' | 'anuncios'; }

export function FileUploader({ type }: Props) {
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);

  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0];
    if (!file) return;
    setUploading(true);
    try {
      const fn = type === 'faturamento'
        ? apiClient.uploadFaturamento.bind(apiClient)
        : apiClient.uploadAnuncios.bind(apiClient);
      await fn(file, setProgress);
    } finally {
      setUploading(false);
      setProgress(0);
    }
  }, [type]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] },
    maxSize: 50 * 1024 * 1024,
    maxFiles: 1,
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors
        ${isDragActive ? 'border-blue-600 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}`}
    >
      <input {...getInputProps()} />
      {uploading ? (
        <div className="space-y-2">
          <p className="text-gray-600">Enviando... {progress}%</p>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div className="bg-blue-600 h-2 rounded-full transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>
      ) : (
        <p className="text-gray-500">
          Arraste um arquivo <strong>.xlsx</strong> ou clique para selecionar
        </p>
      )}
    </div>
  );
}
```

### `RevenueChart.tsx` — Recharts

```tsx
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const BRL = (v: number) => `R$ ${v.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;

export function RevenueChart({ data }: { data: { period: string; revenue: number; debits: number; net: number }[] }) {
  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Receita Mensal</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="period" />
          <YAxis tickFormatter={(v) => `R$ ${(v / 1000).toFixed(0)}k`} />
          <Tooltip formatter={(v: number) => BRL(v)} />
          <Legend />
          <Bar dataKey="revenue" name="Receita" fill="#3b82f6" />
          <Bar dataKey="debits"  name="Débitos" fill="#f97316" />
          <Bar dataKey="net"     name="Líquido" fill="#22c55e" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

## Performance

```tsx
// Code splitting por página
const DashboardPage = lazy(() => import('@/pages/DashboardPage'));
const AnunciosPage  = lazy(() => import('@/pages/AnunciosPage'));

// React Query — cache global
const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5 * 60 * 1000 } },
});

// Layout responsivo (Tailwind)
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
  {cards.map((c) => <MetricCard key={c.title} {...c} />)}
</div>
```

---

## Deploy

```dockerfile
# Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

```bash
# Vercel
vercel --prod

# Netlify
netlify deploy --prod --dir=dist
```

---

## Checklist de migração

```
[ ] Scaffolding: Vite + TypeScript + Tailwind
[ ] Configurar React Router (rotas protegidas)
[ ] Implementar api.ts com interceptors JWT
[ ] Login / Register (useAuth + Zustand)
[ ] Upload faturamento com drag-and-drop e progresso
[ ] Upload anúncios com drag-and-drop e progresso
[ ] Dashboard financeiro (MetricCard + RevenueChart)
[ ] Dashboard anúncios (AnunciosPage + AnunciosChart)
[ ] Histórico de uploads (UploadHistory)
[ ] React Query para cache (staleTime 5 min)
[ ] Code splitting (lazy + Suspense)
[ ] Testes (Vitest + Testing Library)
[ ] Dockerfile + nginx.conf
[ ] Deploy (Vercel / Netlify / Docker)
```

---

Tempo estimado: 3-5 dias (1 dev front-end experiente)
