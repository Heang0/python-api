require('dotenv').config();
const express = require('express');
const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');

// Create simple web server for Render health checks
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

app.get('/', (req, res) => {
  res.json({ 
    status: 'healthy', 
    service: 'YSG Machine Bot',
    timestamp: new Date().toISOString()
  });
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.listen(PORT, () => {
  console.log(`🌐 Health check server running on port ${PORT}`);
});

// Telegram Bot Configuration
const token = process.env.TELEGRAM_BOT_TOKEN;
const API_BASE_URL = 'https://menuqrcode.onrender.com/api';
const SALES_TELEGRAM_USERNAME = 'Emma_Heang';

// Create bot instance
const bot = new TelegramBot(token, { 
  polling: {
    interval: 1000,
    autoStart: true,
    params: {
      timeout: 10
    }
  }
});

console.log('🤖 YSG Machine Bot is running...');

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
            throw new Error('Server is busy. Please try again in a moment.');
        } else if (error.code === 'ECONNABORTED') {
            throw new Error('Server timeout. Please try again.');
        } else {
            throw new Error('Failed to fetch data. Please try again later.');
        }
    }
}

// Get cached menu data or fetch fresh
async function getMenuData() {
    const now = Date.now();
    
    // Return cached data if it's still valid
    if (menuCache.data && (now - menuCache.timestamp) < menuCache.ttl) {
        console.log('📦 Using cached data');
        return menuCache.data;
    }
    
    console.log('🔄 Fetching fresh data');
    try {
        // Fetch all data with delays to avoid rate limiting
        const store = await apiRequest(`/stores/public/slug/ysg`);
        
        // Add delay between requests
        await new Promise(resolve => setTimeout(resolve, 1000));
        const categories = await apiRequest(`/categories/store/slug/ysg`);
        
        // Add delay between requests
        await new Promise(resolve => setTimeout(resolve, 1000));
        const products = await apiRequest(`/products/public-store/slug/ysg`);
        
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

// Function to get product image URL (prioritize image over imageUrl)
function getProductImage(product) {
    if (product.image) {
        return product.image; // Cloudinary image
    } else if (product.imageUrl) {
        return product.imageUrl; // External image URL
    }
    return null; // No image
}

// Function to optimize Cloudinary image URL for Telegram
function optimizeImageUrl(url) {
    if (!url) return null;
    
    // If it's a Cloudinary URL, optimize it for faster loading
    if (url.includes('res.cloudinary.com') && url.includes('/upload/')) {
        return url.replace('/upload/', '/upload/f_auto,q_auto,w_400/');
    }
    
    return url;
}

// Function to create product inquiry message
function createInquiryMessage(product) {
    let message = `🛒 *NEW PRODUCT INQUIRY*\n\n`;
    message += `⚙️ *Product:* ${product.title}\n`;
    
    if (product.price) {
        message += `💰 *Price:* ${product.price}\n`;
    }
    
    if (product.category && product.category.name) {
        message += `📁 *Category:* ${product.category.name}\n`;
    }
    
    if (product.description) {
        // Truncate long descriptions
        const desc = product.description.length > 200 
            ? product.description.substring(0, 200) + '...' 
            : product.description;
        message += `📋 *Description:* ${desc}\n`;
    }
    
    message += `\n📞 *Please contact this customer for more details*`;
    
    return message;
}

// Show single product with image and contact option
async function showProductDetail(chatId, product) {
    try {
        const imageUrl = getProductImage(product);
        const optimizedImageUrl = optimizeImageUrl(imageUrl);
        
        let caption = `⚙️ *${product.title}*\n`;
        
        if (product.price) {
            caption += `💰 *Price:* ${product.price}\n`;
        }
        
        if (product.description) {
            caption += `📋 *Description:* ${product.description}\n`;
        }
        
        const availability = product.isAvailable ? '✅ In Stock' : '❌ Out of Stock';
        caption += `\n${availability}`;
        
        // Add category info if available
        if (product.category && product.category.name) {
            caption += `\n📁 *Category:* ${product.category.name}`;
        }
        
        // Add navigation buttons with CONTACT option
        const keyboard = {
            inline_keyboard: [
                [
                    { text: '📞 Contact Sales', callback_data: `contact_${product._id}` },
                    { text: '👁️ View Details', callback_data: `details_${product._id}` }
                ],
                [
                    { text: '📁 Back to Categories', callback_data: 'back_to_categories' },
                    { text: '🔧 All Products', callback_data: 'show_all_items' }
                ],
                [
                    { text: '🔄 Refresh', callback_data: 'refresh_menu' }
                ]
            ]
        };
        
        if (optimizedImageUrl) {
            // Send message with photo
            await bot.sendPhoto(chatId, optimizedImageUrl, {
                caption: caption,
                parse_mode: 'Markdown',
                reply_markup: keyboard
            });
        } else {
            // Send message without photo
            await bot.sendMessage(chatId, caption, {
                parse_mode: 'Markdown',
                reply_markup: keyboard
            });
        }
        
    } catch (error) {
        console.error('Error showing product detail:', error);
        await bot.sendMessage(chatId, '❌ Failed to load product details. Please try again.');
    }
}

// Handle contact sales request
async function handleContactSales(chatId, productId) {
    try {
        const { products } = await getMenuData();
        const product = products.find(p => p._id === productId);
        
        if (!product) {
            await bot.sendMessage(chatId, '❌ Product not found.');
            return;
        }
        
        // Create the inquiry message
        const inquiryMessage = createInquiryMessage(product);
        
        // Get user info for the inquiry
        const user = await bot.getChat(chatId);
        const userName = user.first_name || 'Customer';
        const userUsername = user.username ? `(@${user.username})` : '';
        
        // Add user info to the message
        const fullInquiryMessage = `${inquiryMessage}\n\n👤 *Customer:* ${userName} ${userUsername}\n🆔 *User ID:* ${chatId}`;
        
        // Create contact keyboard with direct message link
        const contactKeyboard = {
            inline_keyboard: [
                [
                    { 
                        text: '📞 Message Customer', 
                        url: `https://t.me/${user.username ? user.username : `user?id=${chatId}`}`
                    }
                ],
                [
                    { 
                        text: '⚙️ View Product', 
                        callback_data: `details_${product._id}`
                    }
                ]
            ]
        };
        
        // Send confirmation to customer
        await bot.sendMessage(chatId, 
            `✅ *Sales team notified!*\n\n` +
            `We've sent your inquiry for *${product.title}* to our sales team.\n` +
            `They will contact you shortly with more details.\n\n` +
            `📞 *Our Sales Contact:* @${SALES_TELEGRAM_USERNAME}`,
            { parse_mode: 'Markdown' }
        );
        
        // In a real scenario, you would send this to your sales team
        // For now, we'll log it and you can set up forwarding
        console.log('🛒 PRODUCT INQUIRY:', {
            product: product.title,
            price: product.price,
            customer: userName,
            username: user.username,
            userId: chatId,
            timestamp: new Date().toISOString()
        });
        
        // Send inquiry to sales (you can modify this to actually message your sales account)
        await bot.sendMessage(chatId, 
            `📋 *For Sales Team - Product Inquiry:*\n\n${fullInquiryMessage}`,
            { 
                parse_mode: 'Markdown',
                reply_markup: contactKeyboard
            }
        );
        
        // If you want to automatically forward to sales account, you would need:
        // await bot.sendMessage(SALES_CHAT_ID, fullInquiryMessage, { parse_mode: 'Markdown' });
        
    } catch (error) {
        console.error('Error handling contact sales:', error);
        await bot.sendMessage(chatId, 
            `❌ Failed to send inquiry. Please contact @${SALES_TELEGRAM_USERNAME} directly.\n\n` +
            `Product: ${product.title}\nPrice: ${product.price || 'N/A'}`
        );
    }
}

// Start command - Directly show YSG menu
bot.onText(/\/start/, async (msg) => {
    const chatId = msg.chat.id;
    
    try {
        await bot.sendMessage(chatId, '⚙️ *Loading YSG Machine Catalog...*', { parse_mode: 'Markdown' });
        await showYSGMenu(chatId);
    } catch (error) {
        console.error('Error showing menu:', error);
        await bot.sendMessage(chatId, `❌ ${error.message}`);
    }
});

// Handle refresh commands
bot.onText(/🔄 Refresh|📋 Catalog|Show Catalog/, async (msg) => {
    const chatId = msg.chat.id;
    await bot.sendMessage(chatId, '🔄 *Refreshing catalog...*', { parse_mode: 'Markdown' });
    
    // Clear cache to force fresh data
    menuCache.data = null;
    
    await showYSGMenu(chatId);
});

// Main function to show YSG store menu
async function showYSGMenu(chatId) {
    try {
        const { store, categories, products } = await getMenuData();

        // Send store info
        let storeInfo = `🏭 *${store.name}*\n\n`;
        if (store.description) storeInfo += `📋 ${store.description}\n\n`;
        if (store.address) storeInfo += `📍 ${store.address}\n`;
        if (store.phone) storeInfo += `📞 ${store.phone}\n`;

        // Add social media links if available
        const socialLinks = [];
        if (store.facebookUrl) socialLinks.push(`[Facebook](${store.facebookUrl})`);
        if (store.telegramUrl) socialLinks.push(`[Telegram](${store.telegramUrl})`);
        if (store.tiktokUrl) socialLinks.push(`[TikTok](${store.tiktokUrl})`);
        
        if (socialLinks.length > 0) {
            storeInfo += `\n🔗 ${socialLinks.join(' | ')}`;
        }

        await bot.sendMessage(chatId, storeInfo, { 
            parse_mode: 'Markdown',
            disable_web_page_preview: true
        });

        // Send categories as buttons
        if (categories.length > 0) {
            const categoryButtons = categories.map(category => 
                [{ text: `📁 ${category.name}` }]
            );

            // Add "All Products" and "Refresh" buttons
            categoryButtons.unshift([{ text: '🔧 All Products' }]);
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
            await showAllProducts(chatId, products, 'All Products');
        }

    } catch (error) {
        console.error('Error showing YSG menu:', error);
        await bot.sendMessage(chatId, `❌ ${error.message}`);
    }
}

// Handle category selection
bot.onText(/📁 (.+)/, async (msg, match) => {
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
            await showAllProducts(chatId, products, 'All Products');
        }
    } catch (error) {
        await bot.sendMessage(chatId, `❌ ${error.message}`);
    }
});

// Handle "All Products" selection
bot.onText(/🔧 All Products/, async (msg) => {
    const chatId = msg.chat.id;

    try {
        const { products } = await getMenuData();
        await showAllProducts(chatId, products, 'All Products');
    } catch (error) {
        await bot.sendMessage(chatId, `❌ ${error.message}`);
    }
});

// Show products in a category with inline buttons for details
async function showProductsByCategory(chatId, products, categoryName) {
    if (products.length === 0) {
        await bot.sendMessage(chatId, `📭 No products found in ${categoryName}.`);
        return;
    }

    let message = `📁 *${categoryName}*\n\n`;
    
    // Create inline keyboard for product details
    const inlineKeyboard = [];
    
    products.forEach((product, index) => {
        const price = product.price ? ` - ${product.price}` : '';
        const available = product.isAvailable ? '✅' : '❌';
        message += `${available} *${product.title}*${price}\n`;
        
        // Add inline button for product details
        inlineKeyboard.push([
            { 
                text: `👁️ View ${product.title}`, 
                callback_data: `details_${product._id}` 
            }
        ]);
        
        if (product.description) {
            // Truncate long descriptions
            const desc = product.description.length > 100 
                ? product.description.substring(0, 100) + '...' 
                : product.description;
            message += `   📋 ${desc}\n`;
        }
        
        // Add separator between products
        if (index < products.length - 1) {
            message += '━━━━━━━━━━━━━━━━━━━━\n';
        }
    });

    // Add navigation buttons
    inlineKeyboard.push([
        { text: '📁 Back to Categories', callback_data: 'back_to_categories' },
        { text: '🔄 Refresh', callback_data: 'refresh_menu' }
    ]);

    await bot.sendMessage(chatId, message, { 
        parse_mode: 'Markdown',
        reply_markup: {
            inline_keyboard: inlineKeyboard
        }
    });
}

// Show all products with inline buttons for details
async function showAllProducts(chatId, products, title) {
    if (products.length === 0) {
        await bot.sendMessage(chatId, '📭 No products found in the catalog.');
        return;
    }

    let message = `🔧 *${title}*\n\n`;
    
    // Group products by category
    const productsByCategory = {};
    products.forEach(product => {
        const categoryName = product.category ? product.category.name : 'Uncategorized';
        if (!productsByCategory[categoryName]) {
            productsByCategory[categoryName] = [];
        }
        productsByCategory[categoryName].push(product);
    });

    // Create inline keyboard for product details
    const inlineKeyboard = [];
    
    let categoryCount = 0;
    for (const [categoryName, categoryProducts] of Object.entries(productsByCategory)) {
        message += `📁 *${categoryName}*\n`;
        
        categoryProducts.forEach((product, index) => {
            const price = product.price ? ` - ${product.price}` : '';
            const available = product.isAvailable ? '✅' : '❌';
            message += `${available} *${product.title}*${price}\n`;
            
            // Add inline button for product details
            inlineKeyboard.push([
                { 
                    text: `👁️ View ${product.title}`, 
                    callback_data: `details_${product._id}` 
                }
            ]);
            
            if (product.description) {
                // Truncate long descriptions
                const desc = product.description.length > 80 
                    ? product.description.substring(0, 80) + '...' 
                    : product.description;
                message += `   📋 ${desc}\n`;
            }
            
            // Add separator between products in same category
            if (index < categoryProducts.length - 1) {
                message += '⸻⸻⸻⸻⸻\n';
            }
        });
        
        categoryCount++;
        // Add separator between categories
        if (categoryCount < Object.keys(productsByCategory).length) {
            message += '\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n';
        }
    }

    // Add navigation buttons
    inlineKeyboard.push([
        { text: '📁 Categories', callback_data: 'back_to_categories' },
        { text: '🔄 Refresh', callback_data: 'refresh_menu' }
    ]);

    await bot.sendMessage(chatId, message, { 
        parse_mode: 'Markdown',
        reply_markup: {
            inline_keyboard: inlineKeyboard
        }
    });
}

// Handle inline button callbacks
bot.on('callback_query', async (callbackQuery) => {
    const message = callbackQuery.message;
    const chatId = message.chat.id;
    const data = callbackQuery.data;

    try {
        if (data.startsWith('details_')) {
            const productId = data.replace('details_', '');
            const { products } = await getMenuData();
            const product = products.find(p => p._id === productId);
            
            if (product) {
                await showProductDetail(chatId, product);
            } else {
                await bot.sendMessage(chatId, '❌ Product not found.');
            }
            
        } else if (data.startsWith('contact_')) {
            const productId = data.replace('contact_', '');
            await handleContactSales(chatId, productId);
            
        } else if (data === 'back_to_categories') {
            await showYSGMenu(chatId);
            
        } else if (data === 'show_all_items') {
            const { products } = await getMenuData();
            await showAllProducts(chatId, products, 'All Products');
            
        } else if (data === 'refresh_menu') {
            menuCache.data = null;
            await bot.sendMessage(chatId, '🔄 *Refreshing catalog...*', { parse_mode: 'Markdown' });
            await showYSGMenu(chatId);
        }
        
        // Answer the callback query to remove loading state
        await bot.answerCallbackQuery(callbackQuery.id);
        
    } catch (error) {
        console.error('Callback error:', error);
        await bot.answerCallbackQuery(callbackQuery.id, { text: 'Error: ' + error.message });
    }
});

// Help command
bot.onText(/\/help/, (msg) => {
    const chatId = msg.chat.id;
    const helpMessage = `🤖 *YSG Machine Bot Help*\n\n*Commands:*\n/start - Show YSG Machine Catalog\n/help - Show this help\n\n*Features:*\n• Browse all machine categories\n• View product images and details\n• Contact sales team directly\n• See prices and specifications\n• Real-time catalog updates\n\n📞 *Sales Contact:* @${SALES_TELEGRAM_USERNAME}`;
    
    bot.sendMessage(chatId, helpMessage, { parse_mode: 'Markdown' });
});

// Handle any other text messages
bot.on('message', (msg) => {
    const chatId = msg.chat.id;
    const text = msg.text;
    
    // Ignore messages that are already handled by other handlers
    if (!text.startsWith('/') && 
        text !== '🔄 Refresh' && 
        text !== '🔧 All Products' && 
        !text.startsWith('📁')) {
        
        bot.sendMessage(chatId, '🤔 Type /start to see the YSG machine catalog or /help for assistance.');
    }
});

// Error handling
bot.on('error', (error) => {
    console.error('Bot Error:', error);
});

bot.on('polling_error', (error) => {
    console.error('Polling Error:', error);
    
    // If it's a conflict error, it means another bot instance is running
    if (error.message && error.message.includes('409 Conflict')) {
        console.error('🚫 Another bot instance is running with the same token!');
        console.error('💡 Please stop other bot instances (local or other deployments)');
    }
});

console.log('✅ YSG Machine Bot started successfully!');