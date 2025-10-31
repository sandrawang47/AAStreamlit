import streamlit as st
import requests
import hmac
import hashlib
from datetime import datetime
from urllib.parse import quote
import json
import pandas as pd
import time

# Amazon Product Advertising API 5.0 Configuration
class AmazonAPI:
    def __init__(self, access_key, secret_key, partner_tag, marketplace='www.amazon.com'):
        self.access_key = access_key
        self.secret_key = secret_key
        self.partner_tag = partner_tag
        self.marketplace = marketplace
        
        # Map marketplace to region and host
        marketplace_config = {
            'www.amazon.com': {'region': 'us-east-1', 'host': 'webservices.amazon.com'},
            'www.amazon.co.uk': {'region': 'eu-west-1', 'host': 'webservices.amazon.co.uk'},
            'www.amazon.de': {'region': 'eu-west-1', 'host': 'webservices.amazon.de'},
            'www.amazon.fr': {'region': 'eu-west-1', 'host': 'webservices.amazon.fr'},
            'www.amazon.co.jp': {'region': 'us-west-2', 'host': 'webservices.amazon.co.jp'},
            'www.amazon.ca': {'region': 'us-east-1', 'host': 'webservices.amazon.ca'},
        }
        
        config = marketplace_config.get(marketplace, marketplace_config['www.amazon.com'])
        self.region = config['region']
        self.host = config['host']
        self.endpoint = f'https://{self.host}/paapi5'
        
    def search_items(self, keywords, item_count=10, search_index='All'):
        """Search for products by keywords"""
        payload = {
            "PartnerTag": self.partner_tag,
            "PartnerType": "Associates",
            "Keywords": keywords,
            "SearchIndex": search_index,
            "ItemCount": item_count,
            "Resources": [
                "BrowseNodeInfo.BrowseNodes",
                "BrowseNodeInfo.WebsiteSalesRank",
                "CustomerReviews.Count",
                "CustomerReviews.StarRating",
                "Images.Primary.Large",
                "Images.Primary.Medium",
                "Images.Variants.Large",
                "ItemInfo.ByLineInfo",
                "ItemInfo.ContentInfo",
                "ItemInfo.Features",
                "ItemInfo.ManufactureInfo",
                "ItemInfo.ProductInfo",
                "ItemInfo.Title",
                "Offers.Listings.Availability.Message",
                "Offers.Listings.Availability.Type",
                "Offers.Listings.Condition",
                "Offers.Listings.DeliveryInfo.IsAmazonFulfilled",
                "Offers.Listings.DeliveryInfo.IsPrimeEligible",
                "Offers.Listings.IsBuyBoxWinner",
                "Offers.Listings.MerchantInfo",
                "Offers.Listings.Price",
                "Offers.Summaries.HighestPrice",
                "Offers.Summaries.LowestPrice"
            ],
            "Marketplace": self.marketplace
        }
        
        return self._make_request(payload, 'SearchItems')
    
    def get_items(self, item_ids):
        """Get detailed info for specific ASINs"""
        payload = {
            "PartnerTag": self.partner_tag,
            "PartnerType": "Associates",
            "ItemIds": item_ids if isinstance(item_ids, list) else [item_ids],
            "Resources": [
                "BrowseNodeInfo.BrowseNodes",
                "BrowseNodeInfo.BrowseNodes.Ancestor",
                "BrowseNodeInfo.BrowseNodes.SalesRank",
                "BrowseNodeInfo.WebsiteSalesRank",
                "CustomerReviews.Count",
                "CustomerReviews.StarRating",
                "Images.Primary.Small",
                "Images.Primary.Medium",
                "Images.Primary.Large",
                "Images.Variants.Large",
                "ItemInfo.ByLineInfo",
                "ItemInfo.ContentInfo",
                "ItemInfo.Classifications",
                "ItemInfo.Features",
                "ItemInfo.ManufactureInfo",
                "ItemInfo.ProductInfo",
                "ItemInfo.Title",
                "Offers.Listings.Availability.Message",
                "Offers.Listings.Availability.Type",
                "Offers.Listings.Condition",
                "Offers.Listings.DeliveryInfo.IsAmazonFulfilled",
                "Offers.Listings.DeliveryInfo.IsPrimeEligible",
                "Offers.Listings.IsBuyBoxWinner",
                "Offers.Listings.MerchantInfo",
                "Offers.Listings.Price",
                "Offers.Summaries.HighestPrice",
                "Offers.Summaries.LowestPrice",
                "ParentASIN"
            ],
            "Marketplace": self.marketplace
        }
        
        return self._make_request(payload, 'GetItems')
    
    def _make_request(self, payload, operation):
        """Make signed API request with proper AWS Signature Version 4"""
        try:
            payload_json = json.dumps(payload)
            
            timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            date_stamp = datetime.utcnow().strftime('%Y%m%d')
            
            target = f'com.amazon.paapi5.v1.ProductAdvertisingAPIv1.{operation}'
            
            # Create canonical request
            method = 'POST'
            canonical_uri = f'/paapi5/{operation.lower()}'
            canonical_querystring = ''
            
            payload_hash = hashlib.sha256(payload_json.encode('utf-8')).hexdigest()
            
            canonical_headers = f'content-encoding:amz-1.0\ncontent-type:application/json; charset=utf-8\nhost:{self.host}\nx-amz-date:{timestamp}\nx-amz-target:{target}\n'
            signed_headers = 'content-encoding;content-type;host;x-amz-date;x-amz-target'
            
            canonical_request = f'{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'
            
            # Create string to sign
            algorithm = 'AWS4-HMAC-SHA256'
            credential_scope = f'{date_stamp}/{self.region}/ProductAdvertisingAPI/aws4_request'
            string_to_sign = f'{algorithm}\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()}'
            
            # Calculate signature
            def sign(key, msg):
                return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
            
            k_date = sign(('AWS4' + self.secret_key).encode('utf-8'), date_stamp)
            k_region = sign(k_date, self.region)
            k_service = sign(k_region, 'ProductAdvertisingAPI')
            k_signing = sign(k_service, 'aws4_request')
            signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
            
            authorization_header = f'{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'
            
            headers = {
                'content-encoding': 'amz-1.0',
                'content-type': 'application/json; charset=utf-8',
                'host': self.host,
                'x-amz-date': timestamp,
                'x-amz-target': target,
                'Authorization': authorization_header
            }
            
            url = f'https://{self.host}/paapi5/{operation.lower()}'
            
            response = requests.post(url, headers=headers, data=payload_json, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'error': f'HTTP {response.status_code}',
                    'message': response.text,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            return {'error': 'Unexpected error', 'message': str(e), 'type': type(e).__name__}

def extract_product_data(item):
    """Extract product data from API response"""
    data = {
        'asin': item.get('ASIN', 'N/A'),
        'title': item.get('ItemInfo', {}).get('Title', {}).get('DisplayValue', 'N/A'),
        'brand': item.get('ItemInfo', {}).get('ByLineInfo', {}).get('Brand', {}).get('DisplayValue', 'N/A'),
        'manufacturer': item.get('ItemInfo', {}).get('ByLineInfo', {}).get('Manufacturer', {}).get('DisplayValue', 'N/A'),
    }
    
    # Price information
    listings = item.get('Offers', {}).get('Listings', [])
    if listings:
        listing = listings[0]
        data['price'] = listing.get('Price', {}).get('DisplayAmount', 'N/A')
        data['price_amount'] = listing.get('Price', {}).get('Amount', 0)
        data['availability'] = listing.get('Availability', {}).get('Message', 'N/A')
        data['is_prime'] = listing.get('DeliveryInfo', {}).get('IsPrimeEligible', False)
        data['is_amazon_fulfilled'] = listing.get('DeliveryInfo', {}).get('IsAmazonFulfilled', False)
        
        merchant = listing.get('MerchantInfo', {})
        data['merchant_name'] = merchant.get('Name', 'Amazon')
        data['merchant_rating'] = merchant.get('FeedbackRating', 'N/A')
    else:
        data['price'] = 'N/A'
        data['price_amount'] = 0
        data['availability'] = 'N/A'
        data['is_prime'] = False
        data['is_amazon_fulfilled'] = False
        data['merchant_name'] = 'N/A'
        data['merchant_rating'] = 'N/A'
    
    # Reviews
    reviews = item.get('CustomerReviews', {})
    data['rating'] = reviews.get('StarRating', {}).get('Value', 'N/A')
    data['review_count'] = reviews.get('Count', 0)
    
    # Sales Rank
    sales_rank = item.get('BrowseNodeInfo', {}).get('WebsiteSalesRank', {}).get('SalesRank', None)
    data['sales_rank'] = sales_rank if sales_rank else 'N/A'
    
    # Images
    images = item.get('Images', {})
    data['image_url'] = images.get('Primary', {}).get('Large', {}).get('URL', '')
    data['image_medium'] = images.get('Primary', {}).get('Medium', {}).get('URL', '')
    
    # Product details
    product_info = item.get('ItemInfo', {}).get('ProductInfo', {})
    data['color'] = product_info.get('Color', {}).get('DisplayValue', 'N/A')
    data['size'] = product_info.get('Size', {}).get('DisplayValue', 'N/A')
    
    # Features
    features = item.get('ItemInfo', {}).get('Features', {}).get('DisplayValues', [])
    data['features'] = features
    
    # URL
    data['url'] = item.get('DetailPageURL', 'N/A')
    
    return data

def format_social_post(product, platform='facebook'):
    """Format product info for social media"""
    title = product.get('title', 'Product')
    price = product.get('price', 'N/A')
    rating = product.get('rating', 'N/A')
    link = product.get('url', '')
    
    if platform == 'facebook':
        post = f"""🎉 Amazing Deal Alert! 🎉

{title}

💰 Price: {price}
⭐ Rating: {rating} stars
📦 Fast Shipping Available

Get it now: {link}

#AmazonFinds #DealOfTheDay #Shopping #MustHave"""
    else:  # Instagram
        post = f"""✨ {title} ✨

💵 {price}
⭐ {rating} stars

Check out the link in bio! 🔗

#amazon #deals #shopping #musthave #amazonfinds #onlineshopping #dealoftheday"""
    
    return post

# Streamlit UI
st.set_page_config(page_title="Amazon Associates API Suite", page_icon="🛍️", layout="wide")

st.title("🛍️ Amazon Associates API Testing Suite")
st.markdown("Complete toolkit for product research, trending items, and social media automation")

# Sidebar for API credentials
with st.sidebar:
    st.header("⚙️ API Configuration")
    
    st.markdown("### Get Your Credentials:")
    st.markdown("1. Go to [Amazon Product Advertising API](https://webservices.amazon.com/paapi5/documentation/)")
    st.markdown("2. Sign up and get your credentials")
    
    access_key = st.text_input("Access Key ID", type="password", help="Your AWS Access Key ID")
    secret_key = st.text_input("Secret Access Key", type="password", help="Your AWS Secret Access Key")
    partner_tag = st.text_input("Associate Tag", help="Your Amazon Associate ID (e.g., yourname-20)")
    
    marketplace = st.selectbox(
        "Marketplace",
        ["www.amazon.com", "www.amazon.co.uk", "www.amazon.de", "www.amazon.fr", "www.amazon.co.jp", "www.amazon.ca"]
    )
    
    if access_key and secret_key and partner_tag:
        api = AmazonAPI(access_key, secret_key, partner_tag, marketplace)
        st.success("✅ API Configured")
    else:
        st.warning("⚠️ Enter all API credentials above")
        api = None
    
    st.markdown("---")
    debug_mode = st.checkbox("🐛 Debug Mode", help="Show detailed error information")

# Test Connection Button
if api:
    with st.sidebar:
        if st.button("🔌 Test API Connection"):
            with st.spinner("Testing connection..."):
                test_result = api.search_items("test", 1)
                
                if 'error' in test_result:
                    st.error("❌ Connection Failed")
                    if debug_mode:
                        st.json(test_result)
                else:
                    st.success("✅ Connection Successful!")

# Main content tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🎄 Niche Search", 
    "🦦 Trending Tracker", 
    "📊 Product Details", 
    "📱 Social Post Generator",
    "🔥 Trend Analysis",
    "🏆 Bestsellers"
])

# Tab 1: Niche Product Search
with tab1:
    st.header("Function 1: Niche Product Search")
    st.markdown("Search for products in specific niches like Christmas-themed merch")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        niche_query = st.text_input("Enter niche keywords", value="Christmas ornaments")
    with col2:
        niche_count = st.number_input("Results", 1, 10, 5)
    
    if st.button("🔍 Search Niche", key="niche_search"):
        if api:
            with st.spinner("Searching..."):
                results = api.search_items(niche_query, niche_count)
                
                if debug_mode:
                    with st.expander("🐛 Debug Info"):
                        st.json(results)
                
                if 'SearchResult' in results:
                    items = results['SearchResult'].get('Items', [])
                    st.success(f"✅ Found {len(items)} products")
                    
                    for idx, item in enumerate(items, 1):
                        product = extract_product_data(item)
                        
                        with st.expander(f"#{idx}: {product['title'][:80]}...", expanded=idx==1):
                            col_a, col_b = st.columns([1, 2])
                            
                            with col_a:
                                if product['image_url']:
                                    st.image(product['image_url'])
                                
                                if product['is_prime']:
                                    st.success("✓ Prime Eligible")
                                
                            with col_b:
                                st.markdown(f"**{product['title']}**")
                                st.write(f"🏷️ **ASIN:** {product['asin']}")
                                st.write(f"🏭 **Brand:** {product['brand']}")
                                
                                col1, col2, col3 = st.columns(3)
                                col1.metric("💰 Price", product['price'])
                                col2.metric("⭐ Rating", product['rating'])
                                col3.metric("📝 Reviews", product['review_count'])
                                
                                st.write(f"📦 **Availability:** {product['availability']}")
                                st.write(f"🏪 **Seller:** {product['merchant_name']}")
                                
                                if product['features']:
                                    st.write("**✨ Features:**")
                                    for feat in product['features'][:3]:
                                        st.write(f"  • {feat}")
                                
                                st.markdown(f"[🔗 View on Amazon]({product['url']})")
                                
                elif 'error' in results:
                    st.error(f"❌ Error: {results.get('error', 'Unknown error')}")
                    st.write("**Message:**", results.get('message', 'No details available'))
        else:
            st.warning("⚠️ Configure API credentials in the sidebar first!")

# Tab 2: Trending Products Tracker
with tab2:
    st.header("Function 2: Daily Trending Products Tracker")
    st.markdown("Track trending products with specific keywords - Export to CSV for daily tracking")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        trending_keyword = st.text_input("Trending keyword", value="sea otter plush")
    with col2:
        trending_count = st.number_input("Count", 5, 10, 5, key="trend_count")
    
    if st.button("📈 Get Trending Products", key="trending"):
        if api:
            with st.spinner("Fetching trending products..."):
                results = api.search_items(trending_keyword, trending_count)
                
                if 'SearchResult' in results:
                    items = results['SearchResult'].get('Items', [])
                    
                    if items:
                        products_data = []
                        for item in items:
                            product = extract_product_data(item)
                            products_data.append({
                                'ASIN': product['asin'],
                                'Title': product['title'][:60],
                                'Brand': product['brand'],
                                'Price': product['price'],
                                'Rating': product['rating'],
                                'Reviews': product['review_count'],
                                'Sales Rank': product['sales_rank'],
                                'Prime': '✓' if product['is_prime'] else '✗',
                                'Availability': product['availability'],
                                'URL': product['url']
                            })
                        
                        df = pd.DataFrame(products_data)
                        st.dataframe(df, use_container_width=True)
                        
                        # Download button
                        csv = df.to_csv(index=False)
                        st.download_button(
                            "💾 Download CSV",
                            csv,
                            f"trending_{trending_keyword.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv",
                            key='download_csv'
                        )
                        
                        st.success(f"✅ Ready for daily tracking! Save this CSV daily to monitor trends.")
                    else:
                        st.warning("No items found")
                elif 'error' in results:
                    st.error(f"❌ Error: {results.get('error')}")
                    st.write(results.get('message', 'No details'))
        else:
            st.warning("⚠️ Configure API credentials first!")

# Tab 3: Product Details Fetcher
with tab3:
    st.header("Function 3: Real-Time Product Details")
    st.markdown("Fetch comprehensive product details including prices, images, reviews, and specs")
    
    asin_input = st.text_input("Enter ASIN(s) (comma-separated)", placeholder="B0C76343HK, B09XXXXX")
    
    if st.button("🔎 Get Product Details", key="details"):
        if api and asin_input:
            asins = [a.strip() for a in asin_input.split(',')]
            with st.spinner("Fetching product details..."):
                results = api.get_items(asins)
                
                if debug_mode:
                    with st.expander("🐛 API Response"):
                        st.json(results)
                
                if 'ItemsResult' in results:
                    items = results['ItemsResult'].get('Items', [])
                    
                    if items:
                        for item in items:
                            product = extract_product_data(item)
                            
                            st.markdown("---")
                            col1, col2 = st.columns([1, 2])
                            
                            with col1:
                                if product['image_url']:
                                    st.image(product['image_url'])
                                
                                # Display variant images if available
                                variants = item.get('Images', {}).get('Variants', [])
                                if variants:
                                    st.write("**Other Images:**")
                                    img_cols = st.columns(2)
                                    for idx, variant in enumerate(variants[:4]):
                                        with img_cols[idx % 2]:
                                            st.image(variant.get('Large', {}).get('URL', ''), width=100)
                            
                            with col2:
                                st.subheader(product['title'])
                                st.write(f"🏷️ **ASIN:** {product['asin']}")
                                st.write(f"🏭 **Brand:** {product['brand']} by {product['manufacturer']}")
                                
                                col_a, col_b, col_c, col_d = st.columns(4)
                                col_a.metric("💰 Price", product['price'])
                                col_b.metric("⭐ Rating", product['rating'])
                                col_c.metric("📝 Reviews", product['review_count'])
                                col_d.metric("📊 Sales Rank", product['sales_rank'])
                                
                                st.write(f"📦 **Availability:** {product['availability']}")
                                st.write(f"🏪 **Seller:** {product['merchant_name']} (Rating: {product['merchant_rating']})")
                                st.write(f"🎨 **Color:** {product['color']} | 📏 **Size:** {product['size']}")
                                
                                if product['is_prime']:
                                    st.success("✓ Prime Eligible")
                                if product['is_amazon_fulfilled']:
                                    st.info("✓ Fulfilled by Amazon")
                                
                                if product['features']:
                                    st.write("**✨ Product Features:**")
                                    for feat in product['features']:
                                        st.write(f"  • {feat}")
                                
                                st.markdown(f"### [🛒 Buy Now on Amazon]({product['url']})")
                    else:
                        st.warning("No items found with those ASINs")
                elif 'error' in results:
                    st.error(f"❌ Error: {results.get('error')}")
                    st.write(results.get('message'))
        else:
            st.warning("Enter ASIN(s) and configure API!")

# Tab 4: Social Media Post Generator
with tab4:
    st.header("Function 4: Social Media Post Automation")
    st.markdown("Generate formatted posts for Facebook/Instagram with product images")
    
    col1, col2 = st.columns(2)
    with col1:
        social_keyword = st.text_input("Product keyword", value="Christmas gifts", key="social_key")
        platform = st.selectbox("Platform", ["facebook", "instagram"])
    with col2:
        post_count = st.number_input("Number of posts", 1, 5, 3)
    
    if st.button("🎨 Generate Posts", key="social"):
        if api:
            with st.spinner("Generating posts..."):
                results = api.search_items(social_keyword, post_count)
                
                if 'SearchResult' in results:
                    items = results['SearchResult'].get('Items', [])
                    
                    if items:
                        for idx, item in enumerate(items, 1):
                            product = extract_product_data(item)
                            post = format_social_post(product, platform)
                            
                            with st.expander(f"📝 Post {idx}: {product['title'][:50]}...", expanded=True):
                                col_img, col_text = st.columns([1, 2])
                                
                                with col_img:
                                    if product['image_url']:
                                        st.image(product['image_url'], caption="Post Image")
                                        st.caption("Right-click to save image")
                                
                                with col_text:
                                    st.text_area(f"Post Content", post, height=250, key=f"post_{idx}")
                                    
                                    st.write("**Product Details:**")
                                    st.write(f"• Price: {product['price']}")
                                    st.write(f"• Rating: {product['rating']} ⭐ ({product['review_count']} reviews)")
                                    st.write(f"• ASIN: {product['asin']}")
                                    
                                    st.info(f"💡 **Tip:** Download the image and paste this text into {platform.title()}")
                    else:
                        st.warning("No products found")
                elif 'error' in results:
                    st.error(f"❌ Error: {results.get('error')}")
                    st.write(results.get('message'))
        else:
            st.warning("Configure API credentials first!")

# Tab 5: Trend Analysis
with tab5:
    st.header("Function 5: Trend Analysis Dashboard")
    st.markdown("Analyze product trends, pricing, and popularity metrics")
    
    analysis_keyword = st.text_input("Analysis keyword", value="wireless earbuds")
    
    if st.button("📊 Analyze Trends", key="analyze"):
        if api:
            with st.spinner("Analyzing trends..."):
                results = api.search_items(analysis_keyword, 10)
                
                if 'SearchResult' in results:
                    items = results['SearchResult'].get('Items', [])
                    
                    if items:
                        products = [extract_product_data(item) for item in items]
                        
                        # Calculate metrics
                        prices = [p['price_amount'] for p in products if p['price_amount'] > 0]
                        ratings = [float(p['rating']) for p in products if p['rating'] != 'N/A']
                        reviews = [p['review_count'] for p in products]
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Avg Price", f"${sum(prices)/len(prices):.2f}" if prices else "N/A")
                        with col2:
                            st.metric("Avg Rating", f"{sum(ratings)/len(ratings):.1f} ⭐" if ratings else "N/A")
                        with col3:
                            st.metric("Total Reviews", f"{sum(reviews):,}")
                        with col4:
                            prime_count = sum(1 for p in products if p['is_prime'])
                            st.metric("Prime Products", f"{prime_count}/{len(products)}")
                        
                        # Data table
                        df = pd.DataFrame({
                            'Product': [p['title'][:40] + '...' for p in products],
                            'Brand': [p['brand'] for p in products],
                            'Price': [p['price'] for p in products],
                            'Rating': [p['rating'] for p in products],
                            'Reviews': [p['review_count'] for p in products],
                            'Sales Rank': [p['sales_rank'] for p in products],
                            'Prime': ['✓' if p['is_prime'] else '✗' for p in products]
                        })
                        
                        st.subheader("📈 Product Comparison Table")
                        st.dataframe(df, use_container_width=True)
                        
                        # Top performers
                        st.subheader("🏆 Top Rated Products")
                        df_sorted = df.sort_values('Reviews', ascending=False).head(5)
                        st.bar_chart(df_sorted.set_index('Product')['Reviews'])
                        
                        # Download analysis
                        csv = df.to_csv(index=False)
                        st.download_button(
                            "💾 Download Analysis",
                            csv,
                            f"analysis_{analysis_keyword.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv"
                        )
                    else:
                        st.warning("No products found")
                elif 'error' in results:
                    st.error(f"❌ Error: {results.get('error')}")
                    st.write(results.get('message'))
        else:
            st.warning("Configure API credentials first!")


# Tab 6: Bestsellers
with tab6:
    st.header("Function 6: Amazon Bestsellers")
    st.markdown("Get current bestselling products from Amazon")
    
    col1, col2 = st.columns(2)
    with col1:
        bestseller_category = st.text_input("Category keyword", value="electronics")
    with col2:
        bestseller_count = st.number_input("Results", 5, 10, 10, key="best_count")
    
    if st.button("🏆 Get Bestsellers", key="bestsellers"):
        if api:
            with st.spinner("Fetching bestsellers..."):
                results = api.search_items(bestseller_category, bestseller_count)
                
                if 'SearchResult' in results:
                    items = results['SearchResult'].get('Items', [])
                    
                    if items:
                        st.success(f"Top {len(items)} Bestsellers")
                        
                        for idx, item in enumerate(items, 1):
                            with st.container():
                                col1, col2 = st.columns([1, 3])
                                
                                with col1:
                                    if 'Images' in item and 'Primary' in item['Images']:
                                        st.image(item['Images']['Primary']['Large']['URL'])
                                
                                with col2:
                                    st.markdown(f"### #{idx} {item.get('ItemInfo', {}).get('Title', {}).get('DisplayValue', 'N/A')}")
                                    
                                    price = item.get('Offers', {}).get('Listings', [{}])[0].get('Price', {}).get('DisplayAmount', 'N/A')
                                    rating = item.get('CustomerReviews', {}).get('StarRating', {}).get('Value', 'N/A')
                                    
                                    col_a, col_b, col_c = st.columns(3)
                                    col_a.metric("Price", price)
                                    col_b.metric("Rating", f"{rating} ⭐")
                                    col_c.write(f"[View on Amazon]({item.get('DetailPageURL', '#')})")
                                
                                st.markdown("---")
                    else:
                        st.warning("No products found")
                elif 'error' in results:
                    st.error(f"❌ Error: {results.get('error')}")
                    st.write(results.get('message'))
        else:
            st.warning("Configure API credentials first!")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>🛍️ Amazon Associates API Testing Suite | Built with Streamlit</p>
    <p><small>Make sure to comply with Amazon Associates Program Operating Agreement</small></p>
    <p><small>Enable Debug Mode in sidebar to troubleshoot issues</small></p>
</div>
""", unsafe_allow_html=True)