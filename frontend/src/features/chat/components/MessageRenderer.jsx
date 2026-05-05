import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Box, Button, Text } from '@chakra-ui/react';

import { colors } from '@theme/tokens';

/**
 * completeMarkdown — добавляет недостающие закрывающие маркеры,
 * чтобы стриминговый вывод модели парсился корректно (не «ломался»
 * на полпути). Закрывает неполные блоки кода, inline-код,
 * жирный и курсивный текст.
 */
function completeMarkdown(raw) {
  if (!raw || typeof raw !== 'string') return raw || '';

  let text = raw;
  const lines = text.split('\n');
  let inFence = false;
  for (const line of lines) {
    if (/^\s*```/.test(line)) {
      inFence = !inFence;
    }
  }
  if (inFence) {
    text += (text.endsWith('\n') ? '' : '\n') + '```';
  }

  const withoutFences = text.replace(/```[\s\S]*?```/g, '');
  const inlineTicks = (withoutFences.match(/`/g) || []).length;
  if (inlineTicks % 2 === 1) {
    text += '`';
  }

  const boldMatches = text.match(/\*\*/g) || [];
  if (boldMatches.length % 2 === 1) {
    text += '**';
  }

  const cleaned = text.replace(/\*\*[\s\S]*?\*\*/g, '');
  const singleAsterisks = (cleaned.match(/(^|[^*])\*(?!\*)/g) || []).length;
  if (singleAsterisks % 2 === 1) {
    text += '*';
  }

  return text;
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <Button
      size="xs"
      variant="ghost"
      color={copied ? 'green.300' : 'whiteAlpha.600'}
      _hover={{ color: 'white', bg: 'whiteAlpha.200' }}
      onClick={handleCopy}
      position="absolute"
      top={2}
      right={2}
      zIndex={1}
      fontSize="11px"
      h="22px"
      px={2}
    >
      {copied ? '✓ Скопировано' : 'Копировать'}
    </Button>
  );
}

function MessageRenderer({ content }) {
  const MarkdownComponents = {
    code: ({ node, inline, className, children, ...props }) => {
      const match = /language-(\w+)/.exec(className || '');
      const language = match ? match[1] : '';

      if (!inline && match) {
        const codeText = String(children).replace(/\n$/, '');
        return (
          <Box
            position="relative"
            borderRadius="12px"
            overflow="hidden"
            my={3}
            border="1px solid rgba(239,68,68,0.18)"
          >
            <Box
              position="absolute"
              top={0}
              left={0}
              right={0}
              px={3}
              py={1.5}
              bg="rgba(0,0,0,0.55)"
              display="flex"
              alignItems="center"
              justifyContent="space-between"
              zIndex={1}
              borderBottom="1px solid rgba(255,255,255,0.06)"
            >
              <Text fontSize="10.5px" color="rgba(248,113,113,0.85)" fontFamily="'JetBrains Mono', monospace" fontWeight="600" letterSpacing="0.04em" textTransform="lowercase">
                {language}
              </Text>
              <CopyButton text={codeText} />
            </Box>
            <SyntaxHighlighter
              style={vscDarkPlus}
              language={language}
              PreTag="div"
              customStyle={{
                margin: 0,
                borderRadius: 0,
                background: 'rgba(10,10,10,0.6)',
                paddingTop: '2.3rem',
                fontSize: '13px',
              }}
              {...props}
            >
              {codeText}
            </SyntaxHighlighter>
          </Box>
        );
      }

      return (
        <code className={className} {...props}>
          {children}
        </code>
      );
    },
  };

  const safeContent = completeMarkdown(content || '');

  try {
    return (
      <ReactMarkdown components={MarkdownComponents} remarkPlugins={[remarkGfm]}>
        {safeContent}
      </ReactMarkdown>
    );
  } catch (error) {
    console.warn('Markdown parsing error, falling back to plain text:', error);
    return (
      <Text color={colors.text.primary} lineHeight="1.6" whiteSpace="pre-wrap">
        {safeContent}
      </Text>
    );
  }
}

export default MessageRenderer;
