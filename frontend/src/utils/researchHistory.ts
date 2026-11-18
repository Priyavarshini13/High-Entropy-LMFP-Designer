export interface ChatMessage {
  id: string;
  sender: "user" | "copilot";
  text: string;
  direct_answer?: string;
  explanation?: string;
  comparison_table?: any[];
  citations?: any[];
  conflicts_and_limitations?: string;
  timestamp: string;
  attached_image_url?: string;
  attached_image_name?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  timestamp: string;
  dateStr: string;
  candidate?: string | null;
  directAnswerSnippet?: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

// Backwards compatibility interface
export interface ResearchHistoryItem {
  id: string;
  query: string;
  timestamp: string;
  dateStr: string;
  candidate?: string | null;
  directAnswerSnippet?: string;
}

const STORAGE_KEY = "ecmt_chat_sessions";
const LEGACY_KEY = "ecmt_research_history";

/**
 * Retrieve all chat sessions from localStorage.
 * Automatically migrates legacy query-only items if present.
 */
export const getChatSessions = (): ChatSession[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    let sessions: ChatSession[] = [];
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        sessions = parsed;
      }
    }

    // Check legacy storage for migration
    const legacyRaw = localStorage.getItem(LEGACY_KEY);
    if (legacyRaw) {
      try {
        const legacyItems = JSON.parse(legacyRaw);
        if (Array.isArray(legacyItems) && legacyItems.length > 0) {
          const sessionIds = new Set(sessions.map((s) => s.id));
          for (const item of legacyItems) {
            if (!sessionIds.has(item.id)) {
              sessions.push({
                id: item.id || `session-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
                title: item.query || "Research inquiry",
                timestamp: item.timestamp || "",
                dateStr: item.dateStr || "",
                candidate: item.candidate || null,
                directAnswerSnippet: item.directAnswerSnippet,
                messages: [
                  {
                    id: `msg-${Date.now()}-1`,
                    sender: "user",
                    text: item.query || "Research inquiry",
                    timestamp: item.timestamp || "",
                  },
                  ...(item.directAnswerSnippet
                    ? [
                        {
                          id: `msg-${Date.now()}-2`,
                          sender: "copilot" as const,
                          text: item.directAnswerSnippet,
                          direct_answer: item.directAnswerSnippet,
                          timestamp: item.timestamp || "",
                        },
                      ]
                    : []),
                ],
                createdAt: Date.now(),
                updatedAt: Date.now(),
              });
            }
          }
          // Save merged sessions
          localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
        }
      } catch (err) {
        console.warn("Legacy migration notice:", err);
      } finally {
        // Crucial: remove legacy key once migrated so deleted sessions can never be resurrected
        try {
          localStorage.removeItem(LEGACY_KEY);
        } catch {
          // ignore
        }
      }
    }

    // Sort by updatedAt descending
    return sessions.sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
  } catch (err) {
    console.warn("Failed to load chat sessions:", err);
    return [];
  }
};

/**
 * Retrieve a specific chat session by ID.
 */
export const getChatSession = (id: string): ChatSession | undefined => {
  const sessions = getChatSessions();
  return sessions.find((s) => s.id === id);
};

/**
 * Create a new chat session with an initial user message.
 */
export const createChatSession = (
  initialQuery: string,
  candidate?: string | null,
  attachedImageUrl?: string,
  attachedImageName?: string
): ChatSession => {
  const cleanQ = initialQuery.trim();
  const d = new Date();
  const timeStr = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true });
  const dateStr = d.toLocaleDateString([], { month: "short", day: "numeric" });
  const now = Date.now();

  const userMsg: ChatMessage = {
    id: `msg-${now}-u`,
    sender: "user",
    text: cleanQ,
    timestamp: timeStr.toLowerCase(),
    attached_image_url: attachedImageUrl,
    attached_image_name: attachedImageName,
  };

  const newSession: ChatSession = {
    id: `session-${now}-${Math.random().toString(36).substring(2, 7)}`,
    title: cleanQ,
    timestamp: timeStr,
    dateStr: dateStr,
    candidate: candidate || null,
    messages: [userMsg],
    createdAt: now,
    updatedAt: now,
  };

  const current = getChatSessions();
  const updated = [newSession, ...current.filter((s) => s.id !== newSession.id)].slice(0, 50);

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    window.dispatchEvent(new CustomEvent("ecmt_chat_sessions_updated", { detail: updated }));
    // Also dispatch legacy event for backwards compatibility
    window.dispatchEvent(
      new CustomEvent("ecmt_research_history_updated", {
        detail: updated.map((s) => ({
          id: s.id,
          query: s.title,
          timestamp: s.timestamp,
          dateStr: s.dateStr,
          candidate: s.candidate,
          directAnswerSnippet: s.directAnswerSnippet,
        })),
      })
    );
  } catch (err) {
    console.warn("Failed to persist chat session:", err);
  }

  return newSession;
};

/**
 * Add a message to an existing session or update its content.
 */
export const addMessageToSession = (
  sessionId: string,
  message: Omit<ChatMessage, "id">,
  fallbackTitle?: string,
  candidate?: string | null
): ChatSession => {
  const current = getChatSessions();
  let session = current.find((s) => s.id === sessionId);

  const now = Date.now();
  const d = new Date();
  const timeStr = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true });
  const dateStr = d.toLocaleDateString([], { month: "short", day: "numeric" });

  const fullMsg: ChatMessage = {
    ...message,
    id: `msg-${now}-${Math.random().toString(36).substring(2, 6)}`,
  };

  if (!session) {
    session = {
      id: sessionId,
      title: fallbackTitle || message.text.slice(0, 60),
      timestamp: timeStr,
      dateStr: dateStr,
      candidate: candidate || null,
      messages: [fullMsg],
      createdAt: now,
      updatedAt: now,
    };
  } else {
    session.messages.push(fullMsg);
    session.updatedAt = now;
    if (candidate) session.candidate = candidate;
    if (message.direct_answer) {
      session.directAnswerSnippet = message.direct_answer.slice(0, 160);
    }
  }

  const updated = [session, ...current.filter((s) => s.id !== sessionId)].slice(0, 50);

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    window.dispatchEvent(new CustomEvent("ecmt_chat_sessions_updated", { detail: updated }));
    window.dispatchEvent(
      new CustomEvent("ecmt_research_history_updated", {
        detail: updated.map((s) => ({
          id: s.id,
          query: s.title,
          timestamp: s.timestamp,
          dateStr: s.dateStr,
          candidate: s.candidate,
          directAnswerSnippet: s.directAnswerSnippet,
        })),
      })
    );
  } catch (err) {
    console.warn("Failed to update chat session:", err);
  }

  return session;
};

/**
 * Delete a specific chat session by ID.
 */
export const deleteChatSession = (id: string): ChatSession[] => {
  try {
    localStorage.removeItem(LEGACY_KEY);
  } catch {
    // ignore
  }
  const current = getChatSessions();
  const updated = current.filter((s) => s.id !== id);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    window.dispatchEvent(new CustomEvent("ecmt_chat_sessions_updated", { detail: updated }));
    window.dispatchEvent(
      new CustomEvent("ecmt_research_history_updated", {
        detail: updated.map((s) => ({
          id: s.id,
          query: s.title,
          timestamp: s.timestamp,
          dateStr: s.dateStr,
          candidate: s.candidate,
          directAnswerSnippet: s.directAnswerSnippet,
        })),
      })
    );
  } catch (err) {
    console.warn("Failed to delete chat session:", err);
  }
  return updated;
};

/**
 * Clear all chat sessions from storage.
 */
export const clearAllChatSessions = (): void => {
  try {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(LEGACY_KEY);
    window.dispatchEvent(new CustomEvent("ecmt_chat_sessions_updated", { detail: [] }));
    window.dispatchEvent(new CustomEvent("ecmt_research_history_updated", { detail: [] }));
  } catch (err) {
    console.warn("Failed to clear chat sessions:", err);
  }
};

// ----------------------------------------------------------------------------
// Backwards compatibility exports
// ----------------------------------------------------------------------------
export const getResearchHistory = (): ResearchHistoryItem[] => {
  const sessions = getChatSessions();
  return sessions.map((s) => ({
    id: s.id,
    query: s.title,
    timestamp: s.timestamp,
    dateStr: s.dateStr,
    candidate: s.candidate,
    directAnswerSnippet: s.directAnswerSnippet,
  }));
};

export const saveResearchHistoryItem = (
  query: string,
  candidate?: string | null,
  answerSnippet?: string
): ResearchHistoryItem[] => {
  const session = createChatSession(query, candidate);
  if (answerSnippet) {
    session.directAnswerSnippet = answerSnippet.slice(0, 160);
    const sessions = getChatSessions().map((s) => (s.id === session.id ? session : s));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  }
  return getResearchHistory();
};

export const deleteResearchHistoryItem = (id: string): ResearchHistoryItem[] => {
  deleteChatSession(id);
  return getResearchHistory();
};

export const clearResearchHistory = (): void => {
  clearAllChatSessions();
};
