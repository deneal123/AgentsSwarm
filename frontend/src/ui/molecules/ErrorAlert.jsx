import { Alert, AlertDescription, AlertIcon, AlertTitle, CloseButton } from "@chakra-ui/react";

const DEFAULT_TITLE = "Произошла ошибка";
const DEFAULT_DESCRIPTION = "Попробуйте обновить страницу или повторить действие чуть позже.";

function ErrorAlert({ title = DEFAULT_TITLE, description = DEFAULT_DESCRIPTION, onClose }) {
  return (
    <Alert status="error" borderRadius="md" mb={4}>
      <AlertIcon />
      <AlertTitle mr={2}>{title}</AlertTitle>
      <AlertDescription flex="1">{description}</AlertDescription>
      {onClose && <CloseButton onClick={onClose} position="relative" right={-1} top={-1} />}
    </Alert>
  );
}

export default ErrorAlert;
