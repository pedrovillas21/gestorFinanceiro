/**
 * Normaliza o `detail` do FastAPI, que é polimórfico: string em erro de
 * negócio (`raise HTTPException(detail="...")`), array de objetos em erro de
 * validação do Pydantic (`[{loc, msg, type}, ...]`). `PATCH
 * /investments/movements/{id}` devolve o array até dentro de um 422 levantado
 * à mão (`exc.errors()`), então os dois formatos aparecem no mesmo endpoint.
 */

export interface FieldError {
  /** Caminho pontilhado do campo, ex.: "body.new_password". Vazio se não identificável. */
  path: string;
  message: string;
}

export interface NormalizedApiError {
  status: number;
  /** Mensagem pronta para exibir ao usuário, sempre em português. */
  message: string;
  fieldErrors: FieldError[];
}

// Mensagens padrão por código HTTP, usadas quando o `detail` não traz nada
// aproveitável (ausente, ou um formato inesperado). Cobre os nove códigos que
// os endpoints documentados no plano emitem.
const STATUS_MESSAGES: Record<number, string> = {
  400: "Requisição inválida.",
  401: "Sessão expirada ou credenciais inválidas.",
  403: "Você não tem permissão para esta ação.",
  404: "Registro não encontrado.",
  409: "Já existe um registro em conflito com esta operação.",
  413: "Arquivo excede o tamanho permitido.",
  415: "Tipo de arquivo não suportado.",
  422: "Dados inválidos. Confira os campos e tente novamente.",
  429: "Muitas tentativas. Tente novamente mais tarde.",
  500: "Erro interno do servidor. Tente novamente.",
  503: "Serviço temporariamente indisponível.",
};

const DEFAULT_MESSAGE = "Erro inesperado. Tente novamente.";

function normalizeValidationItem(item: unknown): FieldError {
  if (item && typeof item === "object" && "msg" in item) {
    const record = item as { loc?: unknown; msg?: unknown };
    const loc = Array.isArray(record.loc) ? record.loc : [];
    const path = loc
      .filter((segment): segment is string | number => typeof segment === "string" || typeof segment === "number")
      .join(".");
    return { path, message: String(record.msg ?? DEFAULT_MESSAGE) };
  }
  return { path: "", message: DEFAULT_MESSAGE };
}

/**
 * `message` vem `null` quando o `detail` não tinha nada aproveitável — quem
 * chama decide o fallback (normalmente {@link describeApiError}), para não
 * confundir "sem detail" com uma mensagem genérica que parece vinda do servidor.
 */
export function normalizeDetail(detail: unknown): { message: string | null; fieldErrors: FieldError[] } {
  if (typeof detail === "string" && detail.trim()) {
    return { message: detail, fieldErrors: [] };
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const fieldErrors = detail.map(normalizeValidationItem);
    const message = fieldErrors.map((error) => error.message).filter(Boolean).join("; ") || null;
    return { message, fieldErrors };
  }
  return { message: null, fieldErrors: [] };
}

export function describeApiError(status: number, detail: unknown): NormalizedApiError {
  const normalized = normalizeDetail(detail);
  return {
    status,
    message: normalized.message ?? STATUS_MESSAGES[status] ?? DEFAULT_MESSAGE,
    fieldErrors: normalized.fieldErrors,
  };
}

/** Formato mínimo que basta de um erro do axios — evita acoplar este módulo à lib. */
interface AxiosLikeError {
  response?: {
    status: number;
    data?: { detail?: unknown };
  };
}

export function isAxiosLikeError(error: unknown): error is AxiosLikeError {
  return typeof error === "object" && error !== null && "response" in error;
}

/** Ergonômico para telas: `describeError(error)` sem extrair status/detail na mão. */
export function describeError(error: unknown): NormalizedApiError {
  if (isAxiosLikeError(error) && error.response) {
    return describeApiError(error.response.status, error.response.data?.detail);
  }
  return { status: 0, message: DEFAULT_MESSAGE, fieldErrors: [] };
}
