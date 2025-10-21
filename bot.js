require('dotenv').config();
const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');

const token = process.env.TELEGRAM_BOT_TOKEN;
const API_BASE_URL = 'https://menuqrcode.onrender.com/api';

// Create bot instance
const bot = new TelegramBot(token, { polling: true });

console.log('🤖 YSG Menu Bot is running...');

// Helper function to make API requests
async function apiRequest(endpoint) {
    try {
        const response = await axios.get(`${API_BASE_URL}${endpoint}`);
        return response.data;
    } catch (error) {
        console.error('API Error:', error.message);
        throw new Error('Failed to fetch menu data');
    }
}

// Start command - Directly show YSG menu
bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    
    try {
        await showYSGMenu(chatId);
    } catch (error) {
        console.error('Error showing menu:', error);
        await bot.sendMessage(chatId, '❌ Sorry, the menu is currently unavailable. Please try again later.');
    }
});

// Handle refresh commands
bot.onText(/🔄 Refresh|📋 Menu|Show Menu/, async (msg) => {
    const chatId = msg.chat.id;
    await showYSGMenu(chatId);
});

// Main function to show YSG store menu
async function showYSGMenu(chatId) {
    try {
        await bot.sendMessage(chatId, '🍽️ *Loading YSG Store Menu...*', { parse_mode: 'Markdown' });

        // Get store details
        const store = await apiRequest(`/stores/public/slug/ysg`);
        
        // Get categories
        const categories = await apiRequest(`/categories/store/slug/ysg`);
        
        // Get all products
        const products = await apiRequest(`/products/public-store/slug/ysg`);

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
        await bot.sendMessage(chatId, '❌ YSG menu is currently unavailable. Please try again later.');
    }
}

// Handle category selection
bot.onText(/📂 (.+)/, async (msg, match) => {
    const chatId = msg.chat.id;
    const categoryName = match[1];

    try {
        // Get all products and filter by category name
        const products = await apiRequest(`/products/public-store/slug/ysg`);
        const categories = await apiRequest(`/categories/store/slug/ysg`);
        
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
        await bot.sendMessage(chatId, '❌ Error loading category. Please try Refresh.');
    }
});

// Handle "All Items" selection
bot.onText(/🍽️ All Items/, async (msg) => {
    const chatId = msg.chat.id;

    try {
        const products = await apiRequest(`/products/public-store/slug/ysg`);
        await showAllProducts(chatId, products, 'All Items');
    } catch (error) {
        await bot.sendMessage(chatId, '❌ Error loading menu. Please try Refresh.');
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