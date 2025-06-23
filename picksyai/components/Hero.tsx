// file: app/components/Hero.tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FiSend } from 'react-icons/fi';
import { FaGlobe, FaBalanceScale, FaWrench, FaChild } from 'react-icons/fa';
import { epilogue, sora } from '@/app/ui/fonts';

type Message = {
  role: 'user' | 'ai';
  content: any;
};

const TypingLoader = () => {
  const [dots, setDots] = useState('');
  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => (prev.length < 3 ? prev + '.' : ''));
    }, 500);
    return () => clearInterval(interval);
  }, []);
  return (
    <div className="pl-3 text-sm text-white font-medium">Collecting response{dots}</div>
  );
};

function renderFormatted(data: any) {
  console.log('Rendering data:', data); // Debug log
  
  // Handle string responses (error messages)
  if (typeof data === 'string') {
    return (
      <div className="bg-red-900/20 p-4 rounded-xl border border-red-500/30">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 bg-red-500 rounded-full flex items-center justify-center">
            <span className="text-lg">❌</span>
          </div>
          <h2 className="text-xl font-bold text-white">Error</h2>
        </div>
        <p className="text-gray-300 text-sm">{data}</p>
      </div>
    );
  }

  // Handle empty or invalid data
  if (!data || typeof data !== 'object') {
    return (
      <div className="bg-gray-900/20 p-4 rounded-xl border border-gray-500/30">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 bg-gray-500 rounded-full flex items-center justify-center">
            <span className="text-lg">⚠️</span>
          </div>
          <h2 className="text-xl font-bold text-white">No Data</h2>
        </div>
        <p className="text-gray-300 text-sm">No data received from the server.</p>
        <pre className="mt-3 p-2 bg-black rounded text-xs text-gray-400">
          {JSON.stringify(data, null, 2)}
        </pre>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      
      {/* Compact Search Summary */}
      {data.summary && (
        <div className="bg-gradient-to-r from-[#1E1E1E] to-[#2A2A2A] p-4 rounded-xl border border-[#3A3A3A]">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 bg-[#FFC30B] rounded-full flex items-center justify-center">
              <span className="text-lg">🔍</span>
            </div>
            <h2 className="text-xl font-bold text-white">Search Results</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="text-center">
              <p className="text-[#FFC30B] text-xl font-bold">{data.summary.total_deals_found}</p>
              <p className="text-gray-400 text-xs">Deals Found</p>
            </div>
            <div className="text-center">
              <p className="text-white font-semibold text-sm">{data.summary.product_searched}</p>
              <p className="text-gray-400 text-xs">Product</p>
            </div>
            <div className="text-center">
              <p className="text-white font-semibold text-sm">{data.summary.location}</p>
              <p className="text-gray-400 text-xs">Location</p>
            </div>
            <div className="text-center">
              <p className="text-white font-semibold text-sm">{data.summary.search_date}</p>
              <p className="text-gray-400 text-xs">Search Date</p>
            </div>
          </div>
        </div>
      )}

      {/* Compact Deals Display */}
      {Array.isArray(data.deals) && data.deals.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-[#FFC30B] rounded-full flex items-center justify-center">
              <span className="text-lg">🏆</span>
            </div>
            <h2 className="text-xl font-bold text-white">Best Deals</h2>
          </div>
          <div className="space-y-4">
            {data.deals.map((deal: any, index: number) => (
              <div key={index} className={`relative bg-gradient-to-r ${index === 0 ? 'from-[#FFC30B]/10 to-[#1E1E1E]' : 'from-[#1E1E1E] to-[#2A2A2A]'} p-4 rounded-xl border ${index === 0 ? 'border-[#FFC30B]/30' : 'border-[#3A3A3A]'} hover:border-[#FFC30B]/50 transition-all duration-300`}>
                {index === 0 && (
                  <div className="absolute -top-2 -right-2 bg-[#FFC30B] text-black px-2 py-1 rounded-full text-xs font-bold">
                    BEST DEAL
                  </div>
                )}
                
                <div className="flex justify-between items-start mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="bg-[#FFC30B] text-black px-2 py-1 rounded-lg text-xs font-bold">#{index + 1}</span>
                      <span className="bg-blue-600 text-white px-2 py-1 rounded-lg text-xs font-semibold">{deal.platform}</span>
                    </div>
                    <h3 className="font-bold text-base text-white mb-2 line-clamp-2">{deal.product_title}</h3>
                  </div>
                  <div className="text-right ml-3">
                    <div className="text-xl font-bold text-[#FFC30B]">{deal.price}</div>
                    {deal.original_price && (
                      <div className="text-gray-400 line-through text-xs">{deal.original_price}</div>
                    )}
                    {deal.discount && (
                      <div className="bg-green-600 text-white px-2 py-1 rounded-lg text-xs font-bold mt-1">
                        {deal.discount}
                      </div>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 bg-[#FFC30B] rounded-full"></span>
                      <span className="text-gray-300 text-xs"><strong>Seller:</strong> {deal.seller}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
                      <span className="text-gray-300 text-xs"><strong>Rating:</strong> {deal.seller_rating}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
                      <span className="text-gray-300 text-xs"><strong>Stock:</strong> {deal.availability}</span>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 bg-purple-500 rounded-full"></span>
                      <span className="text-gray-300 text-xs"><strong>Delivery:</strong> {deal.delivery}</span>
                    </div>
                  </div>
                </div>

                <div className="mb-3">
                  <p className="text-gray-300 text-xs mb-1"><strong>Key Features:</strong></p>
                  <p className="text-gray-400 text-xs bg-[#0F0F0F] p-2 rounded-lg">{deal.key_features}</p>
                </div>

                <div className="mb-3">
                  <p className="text-gray-300 text-xs mb-1"><strong>Why Recommended:</strong></p>
                  <p className="text-gray-400 text-xs bg-[#0F0F0F] p-2 rounded-lg">{deal.why_recommended}</p>
                </div>

                <div className="flex gap-2">
                  <a 
                    href={deal.direct_link} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="flex-1 bg-[#FFC30B] hover:bg-[#e6b400] text-black font-bold py-2 px-4 rounded-xl text-center text-sm transition-all duration-300 transform hover:scale-105"
                  >
                    View Deal →
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Compact Analysis Section */}
      {data.analysis && (
        <div className="bg-gradient-to-r from-[#1E1E1E] to-[#2A2A2A] p-4 rounded-xl border border-[#3A3A3A]">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 bg-[#FFC30B] rounded-full flex items-center justify-center">
              <span className="text-lg">📊</span>
            </div>
            <h2 className="text-xl font-bold text-white">Deal Analysis</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(data.analysis).map(([key, val]) => (
              <div key={key} className="bg-[#0F0F0F] p-3 rounded-xl">
                <h4 className="text-[#FFC30B] font-semibold mb-1 capitalize text-sm">
                  {key.replace(/_/g, ' ')}
                </h4>
                <p className="text-gray-300 text-xs">
                  {typeof val === 'string' || typeof val === 'number'
                    ? val
                    : val !== null && val !== undefined
                    ? JSON.stringify(val)
                    : 'N/A'}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Compact Recommendations */}
      {data.recommendations && (
        <div className="bg-gradient-to-r from-green-900/20 to-[#1E1E1E] p-4 rounded-xl border border-green-500/30">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
              <span className="text-lg">🤖</span>
            </div>
            <h2 className="text-xl font-bold text-white">AI Recommendations</h2>
          </div>
          <div className="bg-[#0F0F0F] p-3 rounded-xl">
            <p className="text-gray-300 leading-relaxed text-sm">{data.recommendations}</p>
          </div>
        </div>
      )}

      {/* Compact Notes Section */}
      {data.notes && (
        <div className="bg-gradient-to-r from-orange-900/20 to-[#1E1E1E] p-4 rounded-xl border border-orange-500/30">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 bg-orange-500 rounded-full flex items-center justify-center">
              <span className="text-lg">⚠️</span>
            </div>
            <h2 className="text-xl font-bold text-white">Important Notes</h2>
          </div>
          <div className="bg-[#0F0F0F] p-3 rounded-xl">
            <p className="text-gray-300 leading-relaxed text-sm">
              {typeof data.notes === 'string' ? data.notes : JSON.stringify(data.notes)}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

const Hero = () => {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    console.log('Submitting query:', trimmed); // Debug log

    setMessages((prev) => [...prev, { role: 'user', content: trimmed }]);
    setIsLoading(true);
    setQuery('');

    fetch('http://127.0.0.1:8081/picsyai/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_name: trimmed }),
    })
      .then((res) => {
        console.log('Response status:', res.status); // Debug log
        console.log('Response headers:', res.headers); // Debug log
        
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        console.log('Received data:', data); // Debug log
        console.log('Data type:', typeof data); // Debug log
        console.log('Data keys:', Object.keys(data || {})); // Debug log
        
        setMessages((prev) => [...prev, { role: 'ai', content: data }]);
      })
      .catch((error) => {
        console.error('Fetch error:', error); // Debug log
        
        const message = error.message.includes('Failed to fetch')
          ? 'Unable to connect to the server. Please ensure the API is running.'
          : `Error: ${error.message}`;
        setMessages((prev) => [...prev, { role: 'ai', content: message }]);
      })
      .finally(() => {
        console.log('Request completed'); // Debug log
        setIsLoading(false);
      });
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="flex-1 min-h-screen bg-[#2B2B2B] text-white font-sans">
      {/* Main content container - centered in the remaining space after sidebar */}
      <div className="flex flex-col items-center justify-center min-h-screen px-4">
        {!hasMessages ? (
          /* Initial landing page - centered */
          <div className="flex flex-col items-center justify-center w-full max-w-4xl">
            <h1 className={`text-5xl text-[#FFC30B] ${sora.className} font-medium mb-10`}>picksy.ai</h1>
            <form onSubmit={handleSubmit} className="flex items-center bg-white shadow-md rounded-xl w-full max-w-2xl px-4 py-3 mb-6">
              <input 
                type="text" 
                placeholder="Search the product...." 
                className={`${epilogue.className} flex-grow bg-transparent focus:outline-none text-black text-base`} 
                value={query} 
                onChange={(e) => setQuery(e.target.value)} 
              />
              <button type="submit" className="p-2 bg-[#FFC30B] hover:bg-[#e6b400] text-white rounded-lg ml-2">
                <FiSend size={20} />
              </button>
            </form>
            <div className="flex flex-wrap justify-center gap-4">
              <button className="flex items-center gap-2 px-4 py-2 bg-[#EDEDED] text-black rounded-xl text-sm">
                <FaGlobe /> Current Deals
              </button>
              <button className="flex items-center gap-2 px-4 py-2 bg-[#EDEDED] text-black rounded-xl text-sm">
                <FaChild /> Accessories
              </button>
              <button className="flex items-center gap-2 px-4 py-2 bg-[#EDEDED] text-black rounded-xl text-sm">
                <FaBalanceScale /> Compare
              </button>
              <button className="flex items-center gap-2 px-4 py-2 bg-[#EDEDED] text-black rounded-xl text-sm">
                <FaWrench /> Troubleshoot
              </button>
            </div>
          </div>
        ) : (
          /* Chat interface - centered with proper spacing */
          <div className="w-full max-w-4xl flex flex-col h-screen">
            {/* Chat messages container */}
            <div 
              ref={chatRef} 
              className="flex-1 overflow-y-auto space-y-3 px-4 py-6 mb-20"
              style={{ 
                scrollbarWidth: 'none', 
                msOverflowStyle: 'none' 
              }}
            >
              {messages.map((msg, index) => (
                <motion.div 
                  key={index} 
                  initial={{ opacity: 0, y: 10 }} 
                  animate={{ opacity: 1, y: 0 }} 
                  transition={{ duration: 0.4 }} 
                  className={`w-full px-4 py-3 rounded-xl ${epilogue.className} ${
                    msg.role === 'user' 
                      ? 'bg-[#1E1E1E] text-white max-w-2xl mx-auto' 
                      : 'bg-transparent text-white'
                  }`}
                >
                  {msg.role === 'user' ? <p className="text-sm">{msg.content}</p> : renderFormatted(msg.content)}
                </motion.div>
              ))}
              {isLoading && (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }} 
                  animate={{ opacity: 1, y: 0 }} 
                  transition={{ duration: 0.4 }} 
                  className="bg-transparent text-white rounded-xl px-4 py-3 max-w-2xl mx-auto"
                >
                  <TypingLoader />
                </motion.div>
              )}
            </div>

            {/* Fixed input form at bottom - positioned relative to the Hero component */}
            <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 w-[90%] max-w-2xl z-10">
              <form onSubmit={handleSubmit} className="flex items-center bg-white text-black px-4 py-3 rounded-xl shadow-lg">
                <input 
                  type="text" 
                  placeholder="Search the product...." 
                  className={`${epilogue.className} flex-grow bg-transparent focus:outline-none text-base`} 
                  value={query} 
                  onChange={(e) => setQuery(e.target.value)} 
                />
                <button type="submit" className="p-2 bg-[#FFC30B] hover:bg-[#e6b400] text-white rounded-lg ml-2">
                  <FiSend size={20} />
                </button>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Hero;