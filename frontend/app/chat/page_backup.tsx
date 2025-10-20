"use client";

/**
 * Chat Page
 * RAG-powered Q&A interface with document upload
 */

import { useState, useRef, useEffect } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/components/AppLayout";
import FileUpload from "@/components/FileUpload";
import { useAuthStore } from "@/store/authStore";
import { ragAPI } from "@/lib/api";
import type { RAGResponse, Citation } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  id: string;
  type: "user" | "assistant";
  content: string;
  timestamp: Date;
  citations?: Citation[];
  isStreaming?: boolean;
}

export default function ChatPage() {
  const { user } = useAuthStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load messages from localStorage on mount
  useEffect(() => {
    const savedMessages = localStorage.getItem("chatMessages");
    if (savedMessages) {
      try {
        const parsed = JSON.parse(savedMessages);
        // Convert timestamp strings back to Date objects
        const messagesWithDates = parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        }));
        setMessages(messagesWithDates);
      } catch (error) {
        console.error("Failed to load chat history:", error);
      }
    }
  }, []);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem("chatMessages", JSON.stringify(messages));
    }
  }, [messages]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    // Create placeholder for assistant message
    const assistantMessageId = (Date.now() + 1).toString();
    const assistantMessage: Message = {
      id: assistantMessageId,
      type: "assistant",
      content: "",
      timestamp: new Date(),
      isStreaming: true,
    };

    setMessages((prev) => [...prev, assistantMessage]);

    try {
      // Use streaming API
      await ragAPI.generateAnswerStream(
        {
          q: userMessage.content,
          k: 5,
          search_type: "hybrid",
          model: "gpt-4o-mini",
        },
        // On chunk received
        (chunk: string) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: msg.content + chunk }
                : msg
            )
          );
        },
        // On complete (citations received)
        (response: RAGResponse) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    citations: response.citations,
                    isStreaming: false,
                  }
                : msg
            )
          );
          setIsLoading(false);
        },
        // On error
        (error: Error) => {
          console.error("Stream error:", error);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    content: msg.content || `Error: ${error.message}`,
                    isStreaming: false,
                  }
                : msg
            )
          );
          setIsLoading(false);
        }
      );
    } catch (error: any) {
      console.error("Failed to send message:", error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                content: msg.content || `Error: ${error.message || "Failed to generate answer"}`,
                isStreaming: false,
              }
            : msg
        )
      );
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearChat = () => {
    if (confirm("Are you sure you want to clear the chat history?")) {
      setMessages([]);
      localStorage.removeItem("chatMessages");
    }
  };

  return (
    <ProtectedRoute>
      <AppLayout>
        <div className="flex flex-col h-full max-w-4xl mx-auto">
          {/* Welcome Message */}
          {messages.length === 0 && (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center space-y-4">
                <div className="text-6xl">💬</div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Ask anything about your documents
                </h2>
                <p className="text-gray-600 dark:text-gray-400 max-w-md">
                  I'll search through your uploaded documents and provide answers with citations.
                </p>
                <Button
                  onClick={() => setShowUpload(!showUpload)}
                  variant="outline"
                >
                  {showUpload ? "Hide Upload" : "📎 Upload Documents"}
                </Button>
              </div>
            </div>
          )}

          {/* Messages List */}
          {messages.length > 0 && (
            <>
              {/* Chat Header with Clear Button */}
              <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700 mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Chat History
                </h3>
                <Button
                  onClick={handleClearChat}
                  variant="outline"
                  size="sm"
                  className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                  🗑️ Clear Chat
                </Button>
              </div>

              <div className="flex-1 overflow-y-auto space-y-4 pb-4">
                {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${
                    message.type === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-3xl px-4 py-3 rounded-lg ${
                      message.type === "user"
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white"
                    }`}
                  >
                    {/* Message Content */}
                    <div className="prose dark:prose-invert max-w-none prose-headings:font-bold prose-h3:text-lg prose-h3:mt-4 prose-h3:mb-2 prose-p:my-2 prose-ul:my-2 prose-li:my-1">
                      {message.content ? (
                        message.type === "assistant" ? (
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              // Customize heading rendering
                              h3: ({ node, ...props }) => (
                                <h3 className="text-lg font-bold mt-4 mb-2" {...props} />
                              ),
                              h4: ({ node, ...props }) => (
                                <h4 className="text-base font-semibold mt-3 mb-1" {...props} />
                              ),
                              // Customize list rendering
                              ul: ({ node, ...props }) => (
                                <ul className="list-disc list-inside my-2 space-y-1" {...props} />
                              ),
                              ol: ({ node, ...props }) => (
                                <ol className="list-decimal list-inside my-2 space-y-1" {...props} />
                              ),
                              // Customize paragraph rendering
                              p: ({ node, ...props }) => (
                                <p className="my-2 leading-relaxed" {...props} />
                              ),
                              // Customize code blocks
                              code: ({ node, inline, ...props }: any) =>
                                inline ? (
                                  <code className="bg-gray-200 dark:bg-gray-700 px-1 py-0.5 rounded text-sm" {...props} />
                                ) : (
                                  <code className="block bg-gray-200 dark:bg-gray-700 p-2 rounded my-2 text-sm overflow-x-auto" {...props} />
                                ),
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        ) : (
                          message.content
                        )
                      ) : (
                        <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-solid border-current border-r-transparent"></span>
                      )}
                    </div>

                    {/* Citations */}
                    {message.citations && message.citations.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-300 dark:border-gray-600">
                        <p className="text-sm font-medium mb-2">Sources:</p>
                        <div className="flex flex-wrap gap-2">
                          {message.citations.map((citation, idx) => (
                            <Badge
                              key={citation.id}
                              variant="secondary"
                              className="text-xs"
                            >
                              [{idx + 1}] {citation.filename}
                              {citation.page_number && ` (p.${citation.page_number})`}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Timestamp */}
                    <div className="text-xs opacity-70 mt-2">
                      {message.timestamp.toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
              </div>
            </>
          )}

          {/* Upload Section (Collapsible) */}
          {showUpload && (
            <div className="mb-4">
              <FileUpload />
              <Button
                onClick={() => setShowUpload(false)}
                variant="ghost"
                size="sm"
                className="w-full mt-2"
              >
                Hide Upload
              </Button>
            </div>
          )}

          {/* Input Area */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <div className="flex gap-2">
              {!showUpload && messages.length > 0 && (
                <Button
                  onClick={() => setShowUpload(true)}
                  variant="outline"
                  size="icon"
                >
                  📎
                </Button>
              )}
              <div className="flex-1 relative">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask a question about your documents..."
                  disabled={isLoading}
                  rows={3}
                  className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-white"
                />
              </div>
              <Button
                onClick={handleSendMessage}
                disabled={!input.trim() || isLoading}
                className="self-end"
              >
                {isLoading ? (
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-solid border-current border-r-transparent"></span>
                ) : (
                  "Send"
                )}
              </Button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Press Enter to send, Shift+Enter for new line
            </p>
          </div>
        </div>
      </AppLayout>
    </ProtectedRoute>
  );
}
