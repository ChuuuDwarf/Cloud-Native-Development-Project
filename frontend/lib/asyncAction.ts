import { getErrorMessage, logClientError } from './error'

type AsyncActionOptions = {
  fallbackError: string
  context?: string
  setError: (message: string) => void
  setSuccessMessage?: (message: string) => void
  setLoading?: (loading: boolean) => void
  setSubmitting?: (submitting: boolean) => void
  successMessage?: string
}

export async function runClientAction<T>(
  action: () => Promise<T>,
  options: AsyncActionOptions,
): Promise<T | null> {
  const {
    fallbackError,
    context = 'client action failed',
    setError,
    setSuccessMessage,
    setLoading,
    setSubmitting,
    successMessage,
  } = options

  try {
    setLoading?.(true)
    setSubmitting?.(true)
    setError('')
    setSuccessMessage?.('')

    const result = await action()

    if (successMessage) {
      setSuccessMessage?.(successMessage)
    }

    return result
  } catch (error) {
    logClientError(context, error)
    setError(getErrorMessage(error, fallbackError))
    return null
  } finally {
    setLoading?.(false)
    setSubmitting?.(false)
  }
}
