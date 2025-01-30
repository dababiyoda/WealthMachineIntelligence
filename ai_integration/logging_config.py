import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Example logger usage
logger = logging.getLogger('MarketIntelligenceAgent')
logger.debug('Debug logging is enabled for Market Intelligence Agent.')
