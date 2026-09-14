import React, { useState, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import Mascot from './components/Mascot';
import { BookOpen, MessageCircle, Plus, UploadCloud, FileText, Sun, Moon, X, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';

// Playful document viewer panel
const DocumentViewer = ({ file, onClose }) => {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);

  const isPdf = file?.filename?.toLowerCase().endsWith('.pdf');

  useEffect(() => {
    if (!file) return;
    if (isPdf) {
      setLoading(false);
      return;
    }
    setLoading(true);
    axios.get(`http://localhost:8000/files/${file.filename}`)
      .then(res => {
        setContent(res.data.content);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setContent('Error loading file content.');
        setLoading(false);
      });
  }, [file, isPdf]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 24 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="flex-1 flex flex-col h-full bg-transparent relative z-10"
    >
      <div className="p-5 md:p-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-gradient-to-br from-sun to-pink rounded-2xl clay-sm">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="font-display font-extrabold text-lg text-grape dark:text-lime">{file.filename}</h2>
            <p className="text-xs font-bold text-grape/50 dark:text-lavender/50">Document viewer</p>
          </div>
        </div>
        <motion.button
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.92 }}
          onClick={onClose}
          className="p-2.5 bg-white dark:bg-[#2A1F47] text-grape dark:text-lavender rounded-full clay-sm border-2 border-lavender-deep dark:border-grape-dark/60"
        >
          <X className="w-4 h-4" />
        </motion.button>
      </div>
      <div className="flex-1 overflow-y-auto px-5 pb-8 md:px-8">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full space-y-4">
            <Mascot mood="thinking" size={64} />
            <div className="text-grape/50 dark:text-lavender/50 font-bold font-display">Fetching your notes...</div>
          </div>
        ) : isPdf ? (
          <iframe 
            src={`http://localhost:8000/files/${file.filename}/raw`} 
            className="w-full h-full min-h-[75vh] rounded-xl border-[3px] border-lavender-deep dark:border-grape-dark/60 bg-white"
            title="PDF Viewer"
          />
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="max-w-3xl mx-auto whitespace-pre-wrap text-base font-medium text-ink dark:text-lavender leading-relaxed bg-white dark:bg-[#2A1F47] p-8 md:p-10 rounded-xl clay border-[3px] border-lavender-deep dark:border-grape-dark/60"
          >
            {content}
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

function App() {
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);

  const [chats, setChats] = useState([]);
  const [files, setFiles] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [viewingFile, setViewingFile] = useState(null);

  const [isDarkMode, setIsDarkMode] = useState(() => {
    return localStorage.getItem('theme') === 'dark';
  });

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDarkMode]);

  const fetchData = async () => {
    try {
      const [chatsRes, filesRes] = await Promise.all([
        axios.get('http://localhost:8000/chats'),
        axios.get('http://localhost:8000/files')
      ]);
      setChats(chatsRes.data);
      setFiles(filesRes.data);
    } catch (e) {
      console.error('Error fetching sidebar data:', e);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const deleteChat = async (chatId, e) => {
    e.stopPropagation();
    try {
      await axios.delete(`http://localhost:8000/chats/${chatId}`);
      if (currentChatId === chatId) setCurrentChatId(null);
      fetchData();
    } catch (err) {
      console.error("Error deleting chat:", err);
    }
  };

  const deleteFile = async (filename, e) => {
    e.stopPropagation();
    try {
      await axios.delete(`http://localhost:8000/files/${filename}`);
      if (viewingFile?.filename === filename) setViewingFile(null);
      fetchData();
    } catch (err) {
      console.error("Error deleting file:", err);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    setUploadProgress(0);
    setUploadMessage(`Uploading ${file.name}...`);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('http://localhost:8000/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(percentCompleted);
            if (percentCompleted === 100) {
              setUploadMessage(`Digesting ${file.name}...`);
            } else {
              setUploadMessage(`Uploading ${file.name}...`);
            }
          }
        }
      });
      setUploadMessage(`Yum! Indexed ${response.data.chunks_indexed} chunks`);
      setUploadProgress(0);
      setTimeout(() => setUploadMessage(''), 4000);
      fetchData();
    } catch (error) {
      console.error('Upload error', error);
      setUploadMessage('Oops, that upload popped!');
      setUploadProgress(0);
      setTimeout(() => setUploadMessage(''), 4000);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="flex h-screen bg-cream dark:bg-night text-ink dark:text-lavender font-sans overflow-hidden transition-colors duration-300">
      {/* Playful Sidebar */}
      <div className="w-[290px] flex-shrink-0 bg-lavender dark:bg-night-panel flex flex-col z-20 transition-colors duration-300 relative overflow-hidden border-r-2 border-lavender-deep dark:border-grape-dark">
        <div className="p-5 flex items-center justify-between relative z-10">
          <div className="flex items-center gap-2.5">
            <Mascot mood="happy" size={42} className="animate-bounce-soft" />
            <h1 className="text-2xl font-display font-extrabold tracking-tight text-grape dark:text-lime">
              Mnemo
            </h1>
          </div>
          <motion.button
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.9 }}
            onClick={() => setIsDarkMode(!isDarkMode)}
            className="p-2.5 rounded-full bg-white dark:bg-grape-dark/40 text-grape dark:text-sun clay-sm"
          >
            {isDarkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </motion.button>
        </div>

        <div className="px-4 flex-1 overflow-y-auto space-y-6 scrollbar-hide pb-4 relative z-10">
          <motion.button
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.96 }}
            onClick={() => { setCurrentChatId(null); setViewingFile(null); }}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-br from-teal to-teal-dark text-white rounded-2xl px-4 py-3.5 text-sm font-bold font-display clay-sm transition-shadow"
          >
            <Plus className="w-4 h-4 stroke-[3]" />
            New Chat
          </motion.button>

          <div>
            <h2 className="text-[11px] font-extrabold text-grape/50 dark:text-lavender/40 uppercase tracking-widest mb-3 px-2 font-display">Recent Chats</h2>
            <ul className="space-y-1.5">
              {chats.map(chat => (
                <motion.li
                  key={chat.id}
                  whileHover={{ x: 3, scale: 1.02 }}
                  onClick={() => { setCurrentChatId(chat.id); setViewingFile(null); }}
                  className={`group flex items-center justify-between text-sm p-2.5 rounded-2xl cursor-pointer transition-colors font-semibold ${currentChatId === chat.id && !viewingFile ? 'bg-white dark:bg-grape-dark/50 text-grape dark:text-lime clay-sm' : 'text-ink/60 dark:text-lavender/60 hover:bg-white/60 dark:hover:bg-grape-dark/30'}`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <MessageCircle className={`w-4 h-4 flex-shrink-0 ${currentChatId === chat.id && !viewingFile ? 'text-teal' : 'text-grape/40 dark:text-lavender/40'}`} />
                    <span className="truncate">{chat.title}</span>
                  </div>
                  <button 
                    onClick={(e) => deleteChat(chat.id, e)}
                    className="opacity-0 group-hover:opacity-100 hover:text-pink transition-opacity p-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </motion.li>
              ))}
              {chats.length === 0 && (
                <li className="text-xs text-grape/40 dark:text-lavender/30 px-3 py-2 italic font-semibold">No chats yet — say hi!</li>
              )}
            </ul>
          </div>

          <div>
            <h2 className="text-[11px] font-extrabold text-grape/50 dark:text-lavender/40 uppercase tracking-widest mb-3 px-2 font-display">Knowledge Base</h2>
            <ul className="space-y-1.5">
              {files.map(f => (
                <motion.li
                  key={f.filename}
                  whileHover={{ x: 3, scale: 1.02 }}
                  onClick={() => setViewingFile(f)}
                  className={`group flex items-center justify-between text-sm p-2.5 rounded-2xl cursor-pointer transition-colors font-semibold ${viewingFile?.filename === f.filename ? 'bg-white dark:bg-grape-dark/50 text-pink-dark dark:text-pink clay-sm' : 'text-ink/60 dark:text-lavender/60 hover:bg-white/60 dark:hover:bg-grape-dark/30'}`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <BookOpen className={`w-4 h-4 flex-shrink-0 ${viewingFile?.filename === f.filename ? 'text-pink' : 'text-grape/40 dark:text-lavender/40'}`} />
                    <span className="truncate">{f.filename}</span>
                  </div>
                  <button 
                    onClick={(e) => deleteFile(f.filename, e)}
                    className="opacity-0 group-hover:opacity-100 hover:text-pink transition-opacity p-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </motion.li>
              ))}
              {files.length === 0 && (
                <li className="text-xs text-grape/40 dark:text-lavender/30 px-3 py-2 italic font-semibold">No notes uploaded</li>
              )}
            </ul>
          </div>
        </div>

        {/* Upload blob dropzone */}
        <div className="p-4 relative z-10">
          <label className="relative overflow-hidden w-full flex flex-col items-center justify-center border-[3px] border-dashed border-grape/25 dark:border-lavender/20 bg-white/70 dark:bg-grape-dark/20 rounded-xl p-5 cursor-pointer hover:border-sun dark:hover:border-sun hover:bg-sun/10 transition-all group hover-jiggle">
            {uploading ? (
              <motion.div
                animate={{ opacity: [0.8, 1, 0.8] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                className="flex flex-col items-center"
              >
                <div className="mb-2">
                  <Mascot mood="thinking" size={44} />
                </div>
                <span className="text-[11px] font-bold text-grape dark:text-sun text-center max-w-[190px] truncate font-display">{uploadMessage}</span>
                <span className="text-[10px] font-bold text-grape/40 dark:text-lavender/40 mt-0.5">{uploadProgress}%</span>
              </motion.div>
            ) : (
              <>
                <motion.div whileHover={{ y: -3 }} className="flex flex-col items-center">
                  <div className="bg-gradient-to-br from-sun to-pink p-2.5 rounded-full mb-3 clay-sm group-hover:scale-110 transition-transform">
                    <UploadCloud className="w-5 h-5 text-white" />
                  </div>
                  <span className="text-sm font-bold text-ink dark:text-lavender text-center font-display">
                    Feed Mnemo notes
                  </span>
                  <span className="text-[11px] text-grape/40 dark:text-lavender/40 font-bold mt-1">PDF · TXT · MD</span>
                </motion.div>
                <input type="file" className="hidden" onChange={handleFileUpload} accept=".pdf,.txt,.md" />
              </>
            )}
            {!uploading && uploadMessage && (
              <motion.div initial={{ y: 10, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="absolute inset-0 bg-lime/90 flex items-center justify-center rounded-xl">
                <span className="text-xs font-extrabold text-grape font-display px-4 text-center">{uploadMessage}</span>
              </motion.div>
            )}
          </label>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col relative bg-cream dark:bg-night transition-colors">
        <AnimatePresence mode="wait">
          {viewingFile ? (
            <DocumentViewer key="doc-viewer" file={viewingFile} onClose={() => setViewingFile(null)} />
          ) : (
            <motion.div
              key="chat-interface"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={{ duration: 0.3 }}
              className="flex-1 flex flex-col h-full"
            >
              {/* BUGFIX: this used to be key={currentChatId || 'new'}. That forced
                  React to destroy and recreate ChatInterface every time you picked
                  a different chat, which reset its internal activeChatId state to
                  already match the new chatId — so the effect that fetches chat
                  history (which only runs when chatId !== activeChatId) never
                  fired, and the pane stayed blank. Letting the instance persist
                  across chat switches lets that check work as intended. */}
              <ChatInterface
                chatId={currentChatId}
                onChatCreated={(id) => {
                  setCurrentChatId(id);
                  fetchData();
                }}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default App;