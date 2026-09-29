import {
  type UseMutationOptions,
  type UseQueryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import { invoke } from "@tauri-apps/api/core"

export type TauriCommandArgs = Record<string, unknown>

async function tauriInvoke<T>(command: string, args?: TauriCommandArgs): Promise<T> {
  return invoke<T>(command, args)
}

export function useTauriQuery<TData, TError = Error>(
  key: (string | Record<string, unknown>)[],
  command: string,
  args?: TauriCommandArgs,
  options?: Omit<UseQueryOptions<TData, TError>, "queryKey" | "queryFn">
) {
  return useQuery<TData, TError>({
    queryKey: [...key, args],
    queryFn: () => tauriInvoke<TData>(command, args),
    ...options,
  })
}

export function useTauriMutation<TData, TVariables, TError = Error>(
  command: string,
  options?: Omit<UseMutationOptions<TData, TError, TVariables>, "mutationFn">
) {
  return useMutation<TData, TError, TVariables>({
    mutationFn: (variables: TVariables) =>
      tauriInvoke<TData>(command, variables as TauriCommandArgs),
    ...options,
  })
}

export function useTauriInvalidate(key: string[]) {
  const _queryClient = useQueryClient()
  return () => _queryClient.invalidateQueries({ queryKey: key })
}

export async function tauriCommand<T>(command: string, args?: TauriCommandArgs): Promise<T> {
  return tauriInvoke<T>(command, args)
}
