import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, BookOpen } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import ModeBadge from './ModeBadge';
import Mascot from './Mascot';

const ChatInterface = ({ chatId, onChatCreated }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [activeChatId, setActiveChatId] = useState(chatId);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  useEffect(() => {
    if (chatId && chatId !== activeChatId) {
      axios.get(`http://localhost:8000/chats/${chatId}`)
        .then(res => {
          const formatted = res.data.map(m => ({
            id: m.id,
            role: m.role,
            content: m.content,
            mode: m.mode,
            sources: m.sources
          }));
          setMessages(formatted);
          setActiveChatId(chatId);
          setInput('');
        })
        .catch(err => console.error('Error loading chat history:', err));
    } else if (!chatId && activeChatId) {
      setMessages([]);
      setActiveChatId(null);
      setInput('');
    }
  }, [chatId, activeChatId]);

  const handleSend = async () => {
    if (!input.trim()) return;

    let currentId = activeChatId;
    if (!currentId) {
      currentId = Date.now().toString();
      try {
        await axios.post('http://localhost:8000/chats', {
          id: currentId,
          title: input.length > 25 ? input.substring(0, 25) + '...' : input
        });
        setActiveChatId(currentId);
        if (onChatCreated) onChatCreated(currentId);
      } catch (e) {
        console.error('Failed to create chat', e);
        return;
      }
    }

    const userMessage = { id: Date.now(), role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    const assistantMessageId = Date.now() + 1;
    setMessages(prev => [...prev, {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      mode: '',
      sources: []
    }]);

    try {
      const response = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: userMessage.content, chat_id: currentId })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setIsTyping(false);

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      let done = false;
      let buffer = '';

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;

        if (value) {
          buffer += decoder.decode(value, { stream: true });

          const parts = buffer.split('\n\n');
          buffer = parts.pop() || '';

          for (const part of parts) {
            if (part.startsWith('data: ')) {
              const dataStr = part.replace('data: ', '').trim();
              if (!dataStr) continue;

              try {
                const parsed = JSON.parse(dataStr);

                setMessages(prev => prev.map(msg => {
                  if (msg.id === assistantMessageId) {
                    if (parsed.type === 'metadata') {
                      return { ...msg, mode: parsed.mode, sources: parsed.sources };
                    } else if (parsed.type === 'chunk') {
                      return { ...msg, content: msg.content + parsed.text };
                    }
                  }
                  return msg;
                }));

              } catch (e) {
                console.error('Error parsing SSE:', e);
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Query error', error);
      setMessages(prev => prev.map(msg => {
        if (msg.id === assistantMessageId) {
          return { ...msg, content: "Oops, my bubble popped! Something went wrong while I was digging through your notes.", mode: 'Recall' };
        }
        return msg;
      }));
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-full relative bg-transparent">

      <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
        {messages.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1, type: 'spring', stiffness: 200, damping: 18 }}
            className="flex h-full items-center justify-center"
          >
            <div className="text-center max-w-sm">
              <div className="mx-auto mb-5 w-fit animate-floaty">
                <Mascot mood="happy" size={88} />
              </div>
              <h3 className="text-2xl font-display font-extrabold text-grape dark:text-lime mb-2">
                Mnemo's ready to dig in!
              </h3>
              <p className="text-sm font-semibold text-grape/60 dark:text-lavender/60">
                Toss a document into the Knowledge Base, then ask away — I'll go fetch the answers.
              </p>
            </div>
          </motion.div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-6 pb-36">
            <AnimatePresence>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 16, scale: 0.92 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 22 }}
                  className={`flex items-end gap-2.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className="mb-1 flex-shrink-0 hidden sm:block">
                      <Mascot
                        mood={!msg.content ? (msg.mode ? 'talking' : 'thinking') : 'idle'}
                        size={36}
                      />
                    </div>
                  )}
                  <div
                    className={`max-w-[85%] ${
                      msg.role === 'user'
                        ? 'bg-gradient-to-br from-grape to-grape-dark text-white px-5 py-3.5 rounded-lg rounded-br-lg clay-sm'
                        : 'bg-white dark:bg-[#2A1F47] border-[3px] border-lavender-deep dark:border-grape-dark/60 px-6 py-5 rounded-lg rounded-bl-lg clay-sm'
                    }`}
                  >
                    {msg.role === 'assistant' && msg.mode && (
                      <ModeBadge mode={msg.mode} />
                    )}

                    <div className={`text-base leading-relaxed whitespace-pre-wrap font-medium ${msg.role === 'user' ? 'text-white' : 'text-ink dark:text-lavender'}`}>
                      {msg.content || (
                        msg.role === 'assistant' && (
                          <div className="flex items-center gap-2 text-grape/50 dark:text-lavender/50 py-1">
                            <span className="text-sm font-bold font-display animate-pulse">
                              {!msg.mode ? 'Sniffing through your PDFs…' : 'Bubbling up an answer…'}
                            </span>
                          </div>
                        )
                      )}
                    </div>

                    {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                      <div className="mt-4 pt-4 border-t-2 border-dashed border-lavender-deep dark:border-grape-dark/60 flex flex-wrap gap-2">
                        {msg.sources.map((src, idx) => (
                          <motion.span
                            whileHover={{ scale: 1.03 }}
                            key={idx}
                            className="inline-flex items-center text-xs font-bold text-grape dark:text-lime bg-lavender dark:bg-grape-dark/40 px-2.5 py-1.5 rounded-full border-2 border-lavender-deep dark:border-grape-dark cursor-default"
                          >
                            <BookOpen className="w-3 h-3 mr-1.5" />
                            {src.file_name}
                          </motion.span>
                        ))}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Floating Bubble Input */}
      <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-cream dark:from-night via-cream/90 dark:via-night/90 to-transparent pt-20 pointer-events-none">
        <div className="max-w-3xl mx-auto relative animate-glow-clay rounded-xl transition-all duration-300 pointer-events-auto">
          <div className="absolute inset-0 bg-white dark:bg-[#2A1F47] rounded-xl clay border-[3px] border-lavender-deep dark:border-grape-dark/60"></div>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask Mnemo something about your notes..."
            className="relative w-full resize-none rounded-xl bg-transparent py-4 pl-6 pr-16 text-base font-semibold focus:outline-none max-h-32 placeholder:text-grape/40 dark:placeholder:text-lavender/40 text-ink dark:text-lavender"
            rows={1}
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.9 }}
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
            className="absolute right-3 top-3 p-3 rounded-full text-white bg-gradient-to-br from-teal to-teal-dark disabled:from-lavender-deep disabled:to-lavender-deep disabled:text-grape/30 disabled:cursor-not-allowed transition-colors clay-sm"
          >
            <Send className="w-4 h-4" />
          </motion.button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;