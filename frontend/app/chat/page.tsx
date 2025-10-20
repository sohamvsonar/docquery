"use client";

/**
 * Chat Page with Sessions
 * RAG-powered Q&A interface with multiple chat sessions
 */

import { useState, useRef, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/components/AppLayout";
import FileUpload from "@/components/FileUpload";
import { useAuthStore } from "@/store/authStore";
import { ragAPI } from "@/lib/api";
import type { RAGResponse, Citation } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { MessageSquare, Paperclip } from "lucide-react";

interface Message {
  id: string;
  type: "user" | "assistant";
  content: string;
  timestamp: Date;
  citations?: Citation[];
  isStreaming?: boolean;
}

interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

function ChatPageContent() {
  const { user } = useAuthStore();
  const searchParams = useSearchParams();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Get current session
  const currentSession = sessions.find((s) => s.id === currentSessionId);
  const messages = currentSession?.messages || [];

  // Load sessions from localStorage on mount (user-specific)
  useEffect(() => {
    if (!user?.id) return;

    // Clear sessions state when user changes
    setSessions([]);
    setCurrentSessionId(null);

    const userSessionsKey = `chatSessions_user_${user.id}`;
    const userCurrentIdKey = `currentChatSessionId_user_${user.id}`;

    const savedSessions = localStorage.getItem(userSessionsKey);
    const savedCurrentId = localStorage.getItem(userCurrentIdKey);

    if (savedSessions) {
      try {
        const parsed = JSON.parse(savedSessions);
        // Convert date strings back to Date objects
        const sessionsWithDates = parsed.map((session: any) => ({
          ...session,
          createdAt: new Date(session.createdAt),
          updatedAt: new Date(session.updatedAt),
          messages: session.messages.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp),
          })),
        }));
        setSessions(sessionsWithDates);

        // Restore current session
        if (savedCurrentId && sessionsWithDates.find((s: ChatSession) => s.id === savedCurrentId)) {
          setCurrentSessionId(savedCurrentId);
        } else if (sessionsWithDates.length > 0) {
          setCurrentSessionId(sessionsWithDates[0].id);
        }
      } catch (error) {
        console.error("Failed to load chat sessions:", error);
      }
    }
  }, [user?.id]);

  // Save sessions to localStorage whenever they change (user-specific)
  useEffect(() => {
    if (!user?.id) return;

    const userSessionsKey = `chatSessions_user_${user.id}`;
    const userCurrentIdKey = `currentChatSessionId_user_${user.id}`;

    if (sessions.length > 0) {
      localStorage.setItem(userSessionsKey, JSON.stringify(sessions));
    }
    if (currentSessionId) {
      localStorage.setItem(userCurrentIdKey, currentSessionId);
    }
  }, [sessions, currentSessionId, user?.id]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Check for new chat URL parameter
  useEffect(() => {
    const isNewChat = searchParams.get("new");
    if (isNewChat === "true" && user?.id) {
      // Clear the URL parameter first to prevent re-triggering
      window.history.replaceState({}, "", "/chat");

      // Create new session
      const newSession: ChatSession = {
        id: Date.now().toString(),
        title: "New Chat",
        messages: [],
        createdAt: new Date(),
        updatedAt: new Date(),
      };
      setSessions((prev) => [newSession, ...prev]);
      setCurrentSessionId(newSession.id);
    }
  }, [searchParams, user?.id]);

  // Create new chat session
  const handleNewChat = () => {
    const newSession: ChatSession = {
      id: Date.now().toString(),
      title: "New Chat",
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    setSessions((prev) => [newSession, ...prev]);
    setCurrentSessionId(newSession.id);
  };

  // Update session title based on first message
  const updateSessionTitle = (sessionId: string, firstMessage: string) => {
    setSessions((prev) =>
      prev.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              title: firstMessage.slice(0, 50) + (firstMessage.length > 50 ? "..." : ""),
              updatedAt: new Date(),
            }
          : session
      )
    );
  };

  // Delete session
  const handleDeleteSession = (sessionId: string) => {
    if (confirm("Delete this chat?")) {
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        const remaining = sessions.filter((s) => s.id !== sessionId);
        setCurrentSessionId(remaining.length > 0 ? remaining[0].id : null);
      }
    }
  };

  // Clear all sessions
  const handleClearAll = () => {
    if (confirm("Clear all chat history?")) {
      setSessions([]);
      setCurrentSessionId(null);
      localStorage.removeItem("chatSessions");
      localStorage.removeItem("currentChatSessionId");
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return;

    // Store input before clearing
    const messageContent = input.trim();
    setInput("");

    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: messageContent,
      timestamp: new Date(),
    };

    // Create new session if none exists
    let sessionId = currentSessionId;
    if (!sessionId) {
      const newSession: ChatSession = {
        id: Date.now().toString(),
        title: messageContent.slice(0, 50) + (messageContent.length > 50 ? "..." : ""),
        messages: [userMessage],
        createdAt: new Date(),
        updatedAt: new Date(),
      };
      setSessions((prev) => [newSession, ...prev]);
      sessionId = newSession.id;
      setCurrentSessionId(newSession.id);
    } else {
      // Add user message to existing session
      setSessions((prev) =>
        prev.map((session) =>
          session.id === sessionId
            ? {
                ...session,
                messages: [...session.messages, userMessage],
                updatedAt: new Date(),
              }
            : session
        )
      );

      // Update title if this is the first message
      if (currentSession && currentSession.messages.length === 0) {
        updateSessionTitle(sessionId, userMessage.content);
      }
    }

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

    setSessions((prev) =>
      prev.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              messages: [...session.messages, assistantMessage],
            }
          : session
      )
    );

    try {
      await ragAPI.generateAnswerStream(
        {
          q: userMessage.content,
          k: 5,
          search_type: "hybrid",
          model: "gpt-4o-mini",
        },
        (chunk: string) => {
          setSessions((prev) =>
            prev.map((session) =>
              session.id === sessionId
                ? {
                    ...session,
                    messages: session.messages.map((msg) =>
                      msg.id === assistantMessageId
                        ? { ...msg, content: msg.content + chunk }
                        : msg
                    ),
                  }
                : session
            )
          );
        },
        (response: RAGResponse) => {
          setSessions((prev) =>
            prev.map((session) =>
              session.id === sessionId
                ? {
                    ...session,
                    messages: session.messages.map((msg) =>
                      msg.id === assistantMessageId
                        ? {
                            ...msg,
                            citations: response.citations,
                            isStreaming: false,
                          }
                        : msg
                    ),
                  }
                : session
            )
          );
          setIsLoading(false);
        },
        (error: Error) => {
          console.error("Stream error:", error);
          setSessions((prev) =>
            prev.map((session) =>
              session.id === sessionId
                ? {
                    ...session,
                    messages: session.messages.map((msg) =>
                      msg.id === assistantMessageId
                        ? {
                            ...msg,
                            content: msg.content || `Error: ${error.message}`,
                            isStreaming: false,
                          }
                        : msg
                    ),
                  }
                : session
            )
          );
          setIsLoading(false);
        }
      );
    } catch (error: any) {
      console.error("Failed to send message:", error);
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <ProtectedRoute>
      <AppLayout
        chatSessions={sessions}
        currentSessionId={currentSessionId}
        onNewChat={handleNewChat}
        onSelectSession={setCurrentSessionId}
        onDeleteSession={handleDeleteSession}
      >
        <div className="flex flex-col h-full max-w-4xl mx-auto w-full">

          {/* Welcome or Messages */}
          {messages.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center space-y-4">
                <div className="flex items-center justify-center">
                  <MessageSquare className="w-16 h-16 text-blue-500" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Ask anything about your documents
                </h2>
                <p className="text-gray-600 dark:text-gray-400 max-w-md">
                  I'll search through your uploaded documents and provide
                  answers with citations.
                </p>
                <Button
                  onClick={() => setShowUpload(!showUpload)}
                  variant="outline"
                >
                  {showUpload ? "Hide Upload" : "Upload Documents"}
                </Button>
              </div>
            </div>
          ) : (
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
                      <div className="prose dark:prose-invert max-w-none prose-headings:font-bold prose-h3:text-lg prose-h3:mt-4 prose-h3:mb-2 prose-p:my-2 prose-ul:my-2 prose-li:my-1">
                        {message.content ? (
                          message.type === "assistant" ? (
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={{
                                h3: (props: React.HTMLAttributes<HTMLHeadingElement>) => (
                                  <h3 className="text-lg font-bold mt-4 mb-2" {...props} />
                                ),
                                h4: (props: React.HTMLAttributes<HTMLHeadingElement>) => (
                                  <h4 className="text-base font-semibold mt-3 mb-1" {...props} />
                                ),
                                ul: (props: React.HTMLAttributes<HTMLUListElement>) => (
                                  <ul className="list-disc list-inside my-2 space-y-1" {...props} />
                                ),
                                ol: (props: React.HTMLAttributes<HTMLOListElement>) => (
                                  <ol className="list-decimal list-inside my-2 space-y-1" {...props} />
                                ),
                                p: (props: React.HTMLAttributes<HTMLParagraphElement>) => (
                                  <p className="my-2 leading-relaxed" {...props} />
                                ),
                                code: (props: any) => {
                                  const { inline, ...rest } = props as any;
                                  return inline ? (
                                    <code className="bg-gray-200 dark:bg-gray-700 px-1 py-0.5 rounded text-sm" {...rest} />
                                  ) : (
                                    <code className="block bg-gray-200 dark:bg-gray-700 p-2 rounded my-2 text-sm overflow-x-auto" {...rest} />
                                  );
                                },
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
                                {citation.page_number &&
                                  ` (p.${citation.page_number})`}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="text-xs opacity-70 mt-2">
                        {message.timestamp.toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}

            {/* Upload Section */}
            {showUpload && (
              <div className="mb-4 px-4">
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
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4 px-4">
              <div className="flex gap-2">
                {!showUpload && messages.length > 0 && (
                  <Button
                    onClick={() => setShowUpload(true)}
                    variant="outline"
                    size="icon"
                  >
                    <Paperclip className="w-4 h-4" />
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

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="p-4 text-sm text-gray-500">Loading…</div>}>
      <ChatPageContent />
    </Suspense>
  );
}





