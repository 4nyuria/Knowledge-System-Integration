import { entities, relationships } from "../mocks/data";
import type {
    Source,
    Entity,
    Relationship,
    EntityType,
    EntityInput,
} from "../types";

// Simula el retraso de una solicitud real
const delay = <T,>(data: T, ms = 350): Promise<T> => new Promise((resolve) => setTimeout(() => resolve(data), ms));

// Copias en memoria de los datos simulados: los cambios persisten hasta que se recarga la página.
// Cuando el backend esté listo, estas funciones llamarán a la API real en su lugar.
let entityStore: Entity[] = [...entities];
let relationshipStore: Relationship[] = [...relationships];
let nextId = 100;

const idPrefix: Record<EntityType, string> = {
    Cliente: "cli",
    Producto: "pro",
    Pedido: "ped",
};


const requestJson = async <T,>(
    url: string,
    options: RequestInit = {},
): Promise<T> => {
    const response = await fetch(url, {
        ...options,
        credentials: "include",
        headers: {
            ...(options.body ? { "Content-Type": "application/json" } : {}),
            ...options.headers,
        },
    });

    if (!response.ok) {
        let message = `Error HTTP ${response.status} al consultar ${url}`;

        try {
            const errorData = await response.json();
            if (errorData.error) {
                message = errorData.error;
            }
        } catch {
            // La respuesta puede no contener JSON.
        }

        throw new Error(message);
    }

    if (response.status === 204) {
        return undefined as T;
    }

    return (await response.json()) as T;
};
//se cambio el requestJson para relizar mejor el crud.
export type AuthUser = {
    id: number;
    email: string;
    nombre: string;
    rol: string;
};

export const login = (
    email: string,
    password: string,
): Promise<AuthUser> =>
    requestJson<AuthUser>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
    });
//se añadio lo de arriba para evitar tener ya un login luego modificar
export const getCurrentUser = (): Promise<AuthUser> =>
    requestJson<AuthUser>("/api/auth/me");

export const getSources = (): Promise<Source[]> =>
    requestJson<Source[]>("/api/sources");
//los dos exports de arriba son para obtener los datos de la API, 
//por lo que fueron modificados (el anterior dirigia a una prueba de datos mockeados)

export type ImportSourceResult = {
    sourceId: number;
    source: string;
    entityType: EntityType;
    nameColumn: string;
    imported: number;
};

export const importSource = (input: {
    fileName: string;
    columns: string[];
    rows: string[][];
    sourceType: string;
}): Promise<ImportSourceResult> =>
    requestJson<ImportSourceResult>("/api/sources/import", {
        method: "POST",
        body: JSON.stringify(input),
    });

export const getEntities = (): Promise<Entity[]> =>
    requestJson<Entity[]>("/api/entities");

export const getRelationships = (): Promise<Relationship[]> =>
    requestJson<Relationship[]>("/api/relationships");
//los dos exports de arriba son para obtener los datos de la API, 
//por lo que fueron modificados
export const createEntity = (input: EntityInput): Promise<Entity> => {
    const entity: Entity = {
        id: `${idPrefix[input.type]}-${nextId++}`,
        type: input.type,
        name: input.name,
        source: "Manual",
        data: { creado: new Date().toLocaleDateString("es-AR") },
    };

    entityStore = [...entityStore, entity];

    relationshipStore = [
        ...relationshipStore,
        ...input.connectedIds.map((targetId) => ({
            sourceId: entity.id,
            targetId,
            type: input.relationType,
        })),
    ];

    return delay(entity, 200);
};

export const updateEntity = (
    id: string,
    changes: Pick<EntityInput, "name" | "type">,
): Promise<void> => {
    entityStore = entityStore.map((entity) =>
        entity.id === id ? { ...entity, ...changes } : entity,
    );

    return delay(undefined, 200);
};

// Eliminar una entidad también elimina todas las relaciones en las que participa.
export const deleteEntity = (id: string): Promise<void> => {
    entityStore = entityStore.filter((entity) => entity.id !== id);

    relationshipStore = relationshipStore.filter(
        (relationship) =>
            relationship.sourceId !== id && relationship.targetId !== id,
    );

    return delay(undefined, 200);
};