import React, { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { Bot, Send } from "lucide-react";

interface Message {
  id: string;
  type: 'user' | 'ai';
  content: string;
  timestamp: Date;
}

interface AIChatProps {
  messages: Message[];
  isTyping: boolean;
  chatInput: string;
  onChatInputChange: (value: string) => void;
  onSendMessage: () => void;
  onKeyPress: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
}

export const AIChat: React.FC<AIChatProps> = ({
  messages,
  isTyping,
  chatInput,
  onChatInputChange,
  onSendMessage,
  onKeyPress,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Find if the last AI message is empty (streaming hasn't started)
  const lastMessage = messages[messages.length - 1];
  const isWaitingForFirstToken = isTyping && lastMessage?.type === 'ai' && !lastMessage.content;

  return (
    <div className="flex flex-col h-full">
      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 scrollbar-hide">
        {messages.map((message) => {
          // Skip rendering empty AI messages (the placeholder before first token)
          if (message.type === 'ai' && !message.content && isTyping) return null;

          return (
            <div key={message.id}>
              {message.type === 'user' ? (
                /* User message — bubble on right */
                <div className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl px-4 py-2.5 bg-primary text-primary-foreground text-sm">
                    <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
                  </div>
                </div>
              ) : (
                /* AI message — raw text on background, no box */
                <div className="py-1">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Bot className="w-3.5 h-3.5 text-primary" />
                    <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">AI</span>
                  </div>
                  <div className="text-sm text-foreground prose prose-sm dark:prose-invert max-w-none
                    prose-p:my-1.5 prose-p:leading-relaxed prose-p:first:mt-0 prose-p:last:mb-0
                    prose-headings:text-foreground prose-headings:font-semibold prose-headings:mt-3 prose-headings:mb-1.5
                    prose-h1:text-base prose-h2:text-sm prose-h3:text-sm
                    prose-strong:font-bold prose-strong:text-foreground
                    prose-code:text-primary prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:font-mono prose-code:before:content-[''] prose-code:after:content-['']
                    prose-pre:bg-muted prose-pre:text-foreground prose-pre:p-3 prose-pre:rounded-lg prose-pre:my-2 prose-pre:overflow-x-auto prose-pre:border prose-pre:border-border
                    prose-ul:my-1.5 prose-ul:list-disc prose-ul:pl-4 prose-ul:space-y-0.5
                    prose-ol:my-1.5 prose-ol:list-decimal prose-ol:pl-4 prose-ol:space-y-0.5
                    prose-li:text-foreground prose-li:leading-relaxed
                    prose-a:text-primary prose-a:underline
                    prose-blockquote:border-l-2 prose-blockquote:border-primary prose-blockquote:pl-3 prose-blockquote:text-muted-foreground prose-blockquote:my-2
                    prose-hr:border-border prose-hr:my-3">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm, remarkBreaks]}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {/* Single typing indicator — only show when waiting for first token */}
        {isWaitingForFirstToken && (
          <div className="py-1">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Bot className="w-3.5 h-3.5 text-primary" />
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">AI</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              <span className="text-xs text-muted-foreground ml-1">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input */}
      <div className="pt-3 mt-3 border-t border-border/50">
        <div className="flex gap-2 items-end">
          <textarea
            value={chatInput}
            onChange={(e) => onChatInputChange(e.target.value)}
            onKeyPress={onKeyPress}
            placeholder="Ask about your system design..."
            className="flex-1 min-h-[40px] max-h-[100px] px-3 py-2.5 text-sm bg-muted/30 border border-border/50 rounded-xl resize-none focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary/50 transition-colors"
            disabled={isTyping}
            rows={1}
          />
          <button
            onClick={onSendMessage}
            disabled={!chatInput.trim() || isTyping}
            className="h-10 w-10 flex items-center justify-center bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
