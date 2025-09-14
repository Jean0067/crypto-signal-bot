import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
import os
import json
from typing import Dict, List, Optional
import numpy as np

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CryptoSignalBot:
    def __init__(self):
        # Configuration
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '8453398053:AAEX8nNIp5YAkU37aI3HDvks-08RWT1NKik')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', '7089442209')
        
        # CoinGecko API endpoints (no API key required)
        self.coingecko_base = 'https://api.coingecko.com/api/v3'
        
        # Crypto symbols to monitor
        self.crypto_coins = {
            'bitcoin': 'BTC',
            'ethereum': 'ETH', 
            'binancecoin': 'BNB',
            'cardano': 'ADA',
            'polygon': 'MATIC',
            'dogecoin': 'DOGE',
            'solana': 'SOL',
            'chainlink': 'LINK',
            'avalanche-2': 'AVAX',
            'polkadot': 'DOT'
        }
        
        # Technical analysis parameters
        self.rsi_period = 14
        self.ma_short = 20
        self.ma_long = 50
        
        # Store previous data for analysis
        self.previous_data = {}
        
    async def send_telegram_message(self, message: str):
        """Send message to Telegram"""
        try:
            url = f'https://api.telegram.org/bot{self.bot_token}/sendMessage'
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        logger.info("Message sent successfully")
                    else:
                        logger.error(f"Failed to send message: {response.status}")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def fetch_crypto_data(self, coin_id: str) -> Optional[Dict]:
        """Fetch crypto data from CoinGecko"""
        try:
            # Get current price and basic data
            url = f'{self.coingecko_base}/coins/{coin_id}'
            params = {
                'localization': 'false',
                'tickers': 'false',
                'community_data': 'false',
                'developer_data': 'false'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        logger.error(f"Failed to fetch data for {coin_id}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error fetching data for {coin_id}: {e}")
            return None
    
    async def fetch_historical_data(self, coin_id: str, days: int = 30) -> Optional[List]:
        """Fetch historical price data for technical analysis"""
        try:
            url = f'{self.coingecko_base}/coins/{coin_id}/market_chart'
            params = {
                'vs_currency': 'usd',
                'days': str(days),
                'interval': 'hourly' if days <= 7 else 'daily'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('prices', [])
                    else:
                        return None
                        
        except Exception as e:
            logger.error(f"Error fetching historical data for {coin_id}: {e}")
            return None
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return 50.0
            
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)
    
    def calculate_moving_average(self, prices: List[float], period: int) -> float:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return np.mean(prices)
        return np.mean(prices[-period:])
    
    def calculate_macd(self, prices: List[float]) -> Dict:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < 26:
            return {'macd': 0, 'signal': 0, 'histogram': 0}
            
        ema12 = self.calculate_ema(prices, 12)
        ema26 = self.calculate_ema(prices, 26)
        macd_line = ema12 - ema26
        
        # Simple approximation for signal line
        signal_line = macd_line * 0.8  # Simplified signal
        histogram = macd_line - signal_line
        
        return {
            'macd': round(macd_line, 4),
            'signal': round(signal_line, 4),
            'histogram': round(histogram, 4)
        }
    
    def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return np.mean(prices)
            
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
            
        return ema
    
    def analyze_support_resistance(self, prices: List[float]) -> Dict:
        """Simple support and resistance calculation"""
        if len(prices) < 20:
            current_price = prices[-1]
            return {
                'support': current_price * 0.95,
                'resistance': current_price * 1.05
            }
            
        # Find local highs and lows
        recent_prices = prices[-20:]
        support = min(recent_prices)
        resistance = max(recent_prices)
        
        return {
            'support': round(support, 4),
            'resistance': round(resistance, 4)
        }
    
    def generate_signal(self, symbol: str, analysis: Dict) -> Optional[str]:
        """Generate trading signal based on technical analysis"""
        rsi = analysis.get('rsi', 50)
        macd = analysis.get('macd', {})
        price = analysis.get('current_price', 0)
        ma20 = analysis.get('ma20', 0)
        ma50 = analysis.get('ma50', 0)
        support = analysis.get('support', 0)
        resistance = analysis.get('resistance', 0)
        
        signals = []
        signal_strength = 0
        
        # RSI Signals
        if rsi < 30:
            signals.append("🟢 RSI Oversold - Potential BUY")
            signal_strength += 2
        elif rsi > 70:
            signals.append("🔴 RSI Overbought - Potential SELL")
            signal_strength -= 2
        
        # Moving Average Signals
        if ma20 > ma50 and price > ma20:
            signals.append("🟢 Bullish MA Cross")
            signal_strength += 1
        elif ma20 < ma50 and price < ma20:
            signals.append("🔴 Bearish MA Cross")
            signal_strength -= 1
        
        # MACD Signals
        macd_value = macd.get('macd', 0)
        signal_line = macd.get('signal', 0)
        
        if macd_value > signal_line and macd_value > 0:
            signals.append("🟢 MACD Bullish")
            signal_strength += 1
        elif macd_value < signal_line and macd_value < 0:
            signals.append("🔴 MACD Bearish")
            signal_strength -= 1
        
        # Support/Resistance
        if price <= support * 1.02:
            signals.append(f"🟡 Near Support Level: ${support}")
        elif price >= resistance * 0.98:
            signals.append(f"🟡 Near Resistance Level: ${resistance}")
        
        # Generate final signal
        if signal_strength >= 2:
            signal_type = "🚀 STRONG BUY"
        elif signal_strength >= 1:
            signal_type = "🟢 BUY"
        elif signal_strength <= -2:
            signal_type = "💥 STRONG SELL" 
        elif signal_strength <= -1:
            signal_type = "🔴 SELL"
        else:
            signal_type = "⏸️ HOLD"
        
        if signals:  # Only send signal if there are indicators
            message = f"""
🎯 <b>{symbol}/USDT SIGNAL</b>
💰 Price: <b>${price}</b>
📊 Signal: <b>{signal_type}</b>

<b>Technical Analysis:</b>
• RSI (14): {rsi}
• MA20: ${ma20}
• MA50: ${ma50}
• MACD: {macd_value}

<b>Key Levels:</b>
• Support: ${support}
• Resistance: ${resistance}

<b>Indicators:</b>
{chr(10).join(f'• {signal}' for signal in signals)}

⏰ Time: {datetime.now().strftime('%H:%M:%S UTC')}
            """.strip()
            
            return message
        
        return None
    
    async def analyze_crypto(self, coin_id: str, symbol: str):
        """Analyze single cryptocurrency"""
        try:
            # Fetch current data
            current_data = await self.fetch_crypto_data(coin_id)
            if not current_data:
                return
            
            # Fetch historical data for technical analysis
            historical_prices = await self.fetch_historical_data(coin_id, 30)
            if not historical_prices:
                return
            
            # Extract prices
            prices = [price[1] for price in historical_prices]
            current_price = current_data['market_data']['current_price']['usd']
            
            # Calculate technical indicators
            rsi = self.calculate_rsi(prices)
            ma20 = self.calculate_moving_average(prices, 20)
            ma50 = self.calculate_moving_average(prices, 50)
            macd = self.calculate_macd(prices)
            support_resistance = self.analyze_support_resistance(prices)
            
            # Prepare analysis data
            analysis = {
                'current_price': current_price,
                'rsi': rsi,
                'ma20': ma20,
                'ma50': ma50,
                'macd': macd,
                'support': support_resistance['support'],
                'resistance': support_resistance['resistance'],
                'volume_24h': current_data['market_data']['total_volume']['usd'],
                'price_change_24h': current_data['market_data']['price_change_percentage_24h']
            }
            
            # Generate signal
            signal_message = self.generate_signal(symbol, analysis)
            
            if signal_message:
                await self.send_telegram_message(signal_message)
                logger.info(f"Signal sent for {symbol}")
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
    
    async def run_analysis_cycle(self):
        """Run complete analysis cycle for all coins"""
        logger.info("Starting analysis cycle...")
        
        # Send startup message
        startup_msg = f"""
🤖 <b>Crypto Signal Bot Started!</b>

📊 Monitoring: {', '.join(self.crypto_coins.values())}
⏰ Next update in 15 minutes
🎯 Signals based on RSI, MACD, MA analysis

<i>Bot running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>
        """.strip()
        
        await self.send_telegram_message(startup_msg)
        
        # Analyze each cryptocurrency
        for coin_id, symbol in self.crypto_coins.items():
            await self.analyze_crypto(coin_id, symbol)
        
        logger.info("Analysis cycle completed")
    
    async def run_bot(self):
        """Main bot loop"""
        logger.info("Crypto Signal Bot started!")
        
        while True:
            try:
                await self.run_analysis_cycle()
                
                # Wait 15 minutes before next analysis
                logger.info("Waiting 15 minutes for next analysis...")
                await asyncio.sleep(900)  # 15 minutes = 900 seconds
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

async def main():
    """Main function to run the bot"""
    bot = CryptoSignalBot()
    await bot.run_bot()

if __name__ == "__main__":
    asyncio.run(main())