import React, { useEffect, useState } from 'react';

type GPTVisComponent = typeof import('@antv/gpt-vis').GPTVis;
type MarkdownComponents = typeof import('@/components/chat/chat-content/config').default;
type MarkdownPlugins = typeof import('@/components/chat/chat-content/config').markdownPlugins;
type PreprocessLaTeX = typeof import('@/components/chat/chat-content/config').preprocessLaTeX;

const MarkDownContext: React.FC<{ children: string }> = ({ children }) => {
  const [GPTVis, setGPTVis] = useState<GPTVisComponent | null>(null);
  const [components, setComponents] = useState<MarkdownComponents | null>(null);
  const [plugins, setPlugins] = useState<MarkdownPlugins | null>(null);
  const [preprocess, setPreprocess] = useState<PreprocessLaTeX | null>(null);

  useEffect(() => {
    let mounted = true;

    Promise.all([import('@antv/gpt-vis'), import('@/components/chat/chat-content/config')]).then(([gptVis, config]) => {
      if (!mounted) {
        return;
      }
      setGPTVis(() => gptVis.GPTVis);
      setComponents(() => config.default);
      setPlugins(config.markdownPlugins);
      setPreprocess(() => config.preprocessLaTeX);
    });

    return () => {
      mounted = false;
    };
  }, []);

  if (!GPTVis || !components || !plugins || !preprocess) {
    return <div className='whitespace-pre-wrap break-words'>{children}</div>;
  }

  return (
    <GPTVis components={{ ...components }} {...plugins}>
      {preprocess(children)}
    </GPTVis>
  );
};

export default MarkDownContext;
