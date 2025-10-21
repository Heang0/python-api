require('dotenv').config();
const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');

const token = process.env.TELEGRAM_BOT_TOKEN;
const API_BASE_URL = 'https://menuqrcode.onrender.com/api';

// Create bot instance
const bot = new TelegramBot(token, { polling: true });

console.log('🤖 YSG Menu Bot is running...');

// Cache to store menu data (reduces API calls)
let menuCache = {
    data: null,
    timestamp: 0,
    ttl: 5 * 60 * 1000 // 5 minutes cache
};

// Helper function to make API requests with retry logic
async function apiRequest(endpoint) {
    try {
        console.log(`📡 API Request: ${endpoint}`);
        const response = await axios.get(`${API_BASE_URL}${endpoint}`, {
            timeout: 10000, // 10 second timeout
            headers: {
                'User-Agent': 'YSG-Telegram-Bot/1.0'
            }
        });
        return response.data;
    } catch (error) {
        console.error('API Error:', error.response?.status, error.message);
        
        if (error.response?.status === 429) {
            throw new Error('Menu server is busy. Please try again in a moment.');
        } else if (error.code === 'ECONNABORTED') {
            throw new Error('Menu server timeout. Please try again.');
        } else {
            throw new Error('Failed to fetch menu data. Please try again later.');
        }
    }
}

// Get cached menu data or fetch fresh
async function getMenuData() {
    const now = Date.now();
    
    // Return cached data if it's still valid
    if (menuCache.data && (now - menuCache.timestamp) < menuCache.ttl) {
        console.log('📦 Using cached menu data');
        return menuCache.data;
    }
    
    console.log('🔄 Fetching fresh menu data');
    try {
        // Fetch all data in parallel with delays
        const [store, categories, products] = await Promise.all([
            apiRequest(`/stores/public/slug/ysg`),
            new Promise(resolve => setTimeout(() => resolve(apiRequest(`/categories/store/slug/ysg`)), 500)),
            new Promise(resolve => setTimeout(() => resolve(apiRequest(`/products/public-store/slug/ysg`)), 1000))
        ]);
        
        // Cache the data
        menuCache = {
            data: { store, categories, products },
            timestamp: now,
            ttl: 5 * 60 * 1000 // 5 minutes
        };
        
        return menuCache.data;
    } catch (error) {
        // If fresh fetch fails, try to return cached data even if expired
        if (menuCache.data) {
            console.log('⚠️ Using expired cache due to API error');
            return menuCache.data;
        }
        throw error;
    }
}

// Start command - Directly show YSG menu
bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    
    try {
        await bot.sendMessage(chatId, '🍽️ *Loading YSG Store Menu...*', { parse_mode: 'Markdown' });
        await showYSGMenu(chatId);
    } catch (error) {
        console.error('Error showing menu:', error);
        await bot.sendMessage(chatId, `❌ ${error.message}`);
    }
});

// Handle refresh commands
bot.onText(/🔄 Refresh|📋 Menu|Show Menu/, async (msg) => {
    const chatId = msg.chat.id;
    await bot.sendMessage(chatId, '🔄 *Refreshing menu...*', { parse_mode: 'Markdown' });
    await showYSGMenu(chatId);
});

// Main function to show YSG store menu
async function showYSGMenu(chatId) {
    try {
        const { store, categories, products } = await getMenuData();

        // Send store info
        let storeInfo = `🏪 *${store.name}*\n`;
        if (store.description) storeInfo += `📝 ${store.description}\n`;
        if (store.address) storeInfo += `📍 ${store.address}\n`;
        if (store.phone) storeInfo += `📞 ${store.phone}\n`;

        await bot.sendMessage(chatId, storeInfo, { parse_mode: 'Markdown' });

        // Send categories as buttons
        if (categories.length > 0) {
            const categoryButtons = categories.map(category => 
                [{ text: `📂 ${category.name}` }]
            );

            // Add "All Items" and "Refresh" buttons
            categoryButtons.unshift([{ text: '🍽️ All Items' }]);
            categoryButtons.push([{ text: '🔄 Refresh' }]);

            await bot.sendMessage(chatId, '📋 *Select a Category:*', {
                parse_mode: 'Markdown',
                reply_markup: {
                    keyboard: categoryButtons,
                    resize_keyboard: true,
                    one_time_keyboard: false
                }
            });
        } else {
            await showAllProducts(chatId, products, 'All Items');
        }

    } catch (error) {
        console.error('Error showing YSG menu:', error);
        await bot.sendMessage(chatId, `❌ ${error.message}`);
    }
}

// Handle category selection
bot.onText(/📂 (.+)/, async (msg, match) => {
    const chatId = msg.chat.id;
    const categoryName = match[1];

    try {
        const { products, categories } = await getMenuData();
        
        const category = categories.find(cat => cat.name === categoryName);
        if (category) {
            const categoryProducts = products.filter(product => 
                product.category && product.category._id === category._id
            );
            await showProductsByCategory(chatId, categoryProducts, categoryName);
        } else {
            await showAllProducts(chatId, products, 'All Items');
        }
    } catch (error) {
        await bot.sendMessage(chatId, `❌ ${error.message}`);
    }
});

// Handle "All Items" selection
bot.onText(/🍽️ All Items/, async (msg) => {
    const chatId = msg.chat.id;

    try {
        const { products } = await getMenuData();
        await showAllProducts(chatId, products, 'All Items');
    } catch (error) {
        await bot.sendMessage(chatId, `❌ ${error.message}`);
    }
});

// Show products in a category
async function showProductsByCategory(chatId, products, categoryName) {
    if (products.length === 0) {
        await bot.sendMessage(chatId, `📭 No items found in ${categoryName}.`);
        return;
    }

    let message = `📂 *${categoryName}*\n\n`;
    
    products.forEach((product) => {
        const price = product.price ? ` - ${product.price}` : '';
        const available = product.isAvailable ? '✅' : '❌';
        message += `${available} *${product.title}*${price}\n`;
        
        if (product.description) {
            message += `   📝 ${product.description}\n`;
        }
        
        message += '\n';
    });

    // Add refresh button
    message += '\n🔄 Tap "Refresh" to see latest menu';

    await bot.sendMessage(chatId, message, { 
        parse_mode: 'Markdown',
        reply_markup: {
            keyboard: [[{ text: '🔄 Refresh' }]],
            resize_keyboard: true
        }
    });
}

// Show all products
async function showAllProducts(chatId, products, title) {
    if (products.length === 0) {
        await bot.sendMessage(chatId, '📭 No items found in the menu.');
        return;
    }

    let message = `🍽️ *${title}*\n\n`;
    
    // Group products by category
    const productsByCategory = {};
    products.forEach(product => {
        const categoryName = product.category ? product.category.name : 'Uncategorized';
        if (!productsByCategory[categoryName]) {
            productsByCategory[categoryName] = [];
        }
        productsByCategory[categoryName].push(product);
    });

    for (const [categoryName, categoryProducts] of Object.entries(productsByCategory)) {
        message += `📂 *${categoryName}*\n`;
        
        categoryProducts.forEach(product => {
            const price = product.price ? ` - ${product.price}` : '';
            const available = product.isAvailable ? '✅' : '❌';
            message += `${available} *${product.title}*${price}\n`;
            
            if (product.description) {
                message += `   📝 ${product.description}\n`;
            }
        });
        
        message += '\n';
    }

    // Add refresh button
    message += '\n🔄 Tap "Refresh" to see latest menu';

    await bot.sendMessage(chatId, message, { 
        parse_mode: 'Markdown',
        reply_markup: {
            keyboard: [[{ text: '🔄 Refresh' }]],
            resize_keyboard: true
        }
    });
}

// Help command
bot.onText(/\/help/, (msg) => {
    const chatId = msg.chat.id;
    const helpMessage = `🤖 *YSG Menu Bot Help*\n\n*Commands:*\n/start - Show YSG Store Menu\n/help - Show this help\n\n*Features:*\n• Browse all menu categories\n• See prices and descriptions\n• Real-time menu updates\n\n🔄 Use Refresh button to get latest menu`;
    
    bot.sendMessage(chatId, helpMessage, { parse_mode: 'Markdown' });
});

console.log('✅ YSG Menu Bot started successfully!');