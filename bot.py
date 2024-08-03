import xi.sdk.resellers
import openai
from openai import OpenAI
import logging
import time
import asyncio
import uuid
from dotenv import load_dotenv
import os
from xi.sdk.resellers.rest import ApiException
from xi.sdk.resellers.api.accesstoken_api import AccesstokenApi
from xi.sdk.resellers.api.product_catalog_api import ProductCatalogApi
from xi.sdk.resellers.models.price_and_availability_request import PriceAndAvailabilityRequest
from xi.sdk.resellers.models.price_and_availability_request_products_inner import PriceAndAvailabilityRequestProductsInner
from botbuilder.core import TurnContext, ActivityHandler
from botbuilder.schema import ChannelAccount
from pprint import pprint
from office365.graph_client import GraphClient
import pandas as pd
from io import BytesIO
from config import CONFIG


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI()

class ExcelAPI:
    def __init__(self):
        self.client_id = CONFIG.AZURE_CLIENT_ID
        self.client_secret = CONFIG.AZURE_CLIENT_SECRET
        self.tenant_id = CONFIG.AZURE_TENANT_ID
        self.site_url = CONFIG.SHAREPOINT_SITE_URL
        self.file_path = CONFIG.EXCEL_FILE_URL

    async def get_excel_data(self):
        if not await self.test_graph_access():
            raise Exception("Failed to access Microsoft Graph. Please check your credentials and permissions.")

        try:
            client = GraphClient.with_client_secret(self.tenant_id, self.client_id, self.client_secret)
            site = client.sites.get_by_url(self.site_url).get().execute_query()
            drives = site.drives.get().execute_query()

            if not drives:
                raise Exception("No drives found in the site")

            drive = drives[0]
            file = drive.root.get_by_path(self.file_path).get().execute_query()
            content = file.get_content().execute_query()

            if not isinstance(content, bytes):
                if hasattr(content, 'value'):
                    content = content.value

            df = pd.read_excel(BytesIO(content))
            return df

        except Exception as e:
            logger.error(f"Unexpected error in get_excel_data: {str(e)}")
            raise

    async def test_graph_access(self):
        try:
            client = GraphClient.with_client_secret(self.tenant_id, self.client_id, self.client_secret)
            site = client.sites.get_by_url(self.site_url).get().execute_query()
            return True
        except Exception as e:
            logger.error(f"Error accessing Graph API: {str(e)}")
            return False

    def search_products(self, df, keywords):
        keywords_set = set(keywords.lower().split())
        
        def match_keywords(row):
            text = (str(row['Description']).lower() +
                    str(row['Category']).lower() +
                    str(row['Sub Category']).lower())
            return all(keyword in text for keyword in keywords_set)
        
        results = df[df.apply(match_keywords, axis=1)]
        return results

    def format_results(self, results):
        formatted_results = []
        for _, row in results.iterrows():
            formatted_result = []
            for column, value in row.items():
                # Strip whitespace from both column name and value
                column = column.strip()
                if isinstance(value, str):
                    value = value.strip()
                
                if value is not None and str(value).strip():  # Only include non-empty values
                    formatted_result.append(f"**{column}**: {value}")
            formatted_results.append("  \n".join(formatted_result))  # Join with newline
        return "\n\n".join(formatted_results)  # Join products with double newline

class IngramMicroBot(ActivityHandler):
    def __init__(self):
        super().__init__()
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.client_id = os.environ.get("INGRAM_CLIENT_ID")
        self.client_secret = os.environ.get("INGRAM_CLIENT_SECRET")
        self.access_token = None
        self.token_expiry = 0
        self.page_number = 1
        self.search_term = None
        self.only_available = False
        self.excel_api = ExcelAPI()
        self.excel_data = None

    async def load_excel_data(self):
        try:
            self.excel_data = await self.excel_api.get_excel_data()
            logger.info("Excel data loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Excel data: {str(e)}")

    async def get_access_token(self):
        configuration = xi.sdk.resellers.Configuration(
            host="https://api.ingrammicro.com:443"
        )

        with xi.sdk.resellers.ApiClient(configuration) as api_client:
            api_instance = AccesstokenApi(api_client)
            grant_type = 'client_credentials'

            try:
                api_response = api_instance.get_accesstoken(grant_type, self.client_id, self.client_secret)
                self.access_token = api_response.access_token
                self.token_expiry = int(time.time()) + int(api_response.expires_in)  # Set expiry time
                logger.debug(f"New access token obtained. Expires at {self.token_expiry}")
                return self.access_token
            except ApiException as e:
                logger.error(f"Exception when calling AccesstokenApi->get_accesstoken: {e}")
                raise

    async def ensure_access_token(self):
        current_time = int(time.time())
        if not self.access_token or current_time >= self.token_expiry:
            await self.get_access_token()
        return self.access_token


    async def handle_generic_question(self, turn_context: TurnContext, question: str) -> bool:
        logger.debug(f"Attempting to handle generic question: {question}")
        try:
            system_message = (
                "You are an assistant helping employees provide relevant product information to customers. "
                "When asked a question, provide correct, concise, relevant, and to-the-point answers. "
                "In your answers please do not mention anything about your latest update. "
                "Make sure to include the most up-to-date and accurate information, particularly for product releases and specifications."
            )

            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": question}
                ],
                max_tokens=300  # Adjust this value as needed for response length
            )
            answer = response.choices[0].message.content
            
            logger.debug(f"OpenAI response received: {answer}")
            
            # Check if the response is meaningful
            if "I don't know" in answer.lower() or "I'm not sure" in answer.lower():
                logger.debug("OpenAI response was not meaningful")
                return False
            
            await turn_context.send_activity(answer)
            return True
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            await turn_context.send_activity(f"An error occurred while processing your question: {str(e)}")
            return False

    async def on_message_activity(self, turn_context: TurnContext):
        message_text = turn_context.activity.text
        logger.debug(f"Received message: {message_text}")

        if message_text.lower().startswith("excel search for "):
            search_term = message_text[17:].strip()
            handled = await self.search_excel_products(turn_context, search_term)
            if handled:
                return  # Exit the method if the Excel search was handled

        if message_text.lower().startswith("price and availability for "):
            part_number = message_text[26:].strip()
            await self.get_price_and_availability(turn_context, part_number)
        
        elif message_text.lower().startswith("search for available "):
            self.search_term = message_text[21:]
            self.page_number = 1
            self.only_available = True
            await self.search_product(turn_context, self.search_term, self.page_number, only_available=True)
        
        elif message_text.lower().startswith("search for product "):
            self.search_term = message_text[19:]
            self.page_number = 1
            self.only_available = False
            await self.search_product(turn_context, self.search_term, self.page_number, only_available=False)
        
        elif message_text.lower() == "next":
            if self.search_term:
                self.page_number += 1
                await turn_context.send_activity(f"Loading page {self.page_number} for: {self.search_term}")
                await self.search_product(turn_context, self.search_term, self.page_number, only_available=self.only_available)
            else:
                await turn_context.send_activity("No active search. Please start a new search.")
        
        elif message_text.lower() == "previous":
            if self.search_term:
                if self.page_number > 1:
                    self.page_number -= 1
                    await self.search_product(turn_context, self.search_term, self.page_number, only_available=self.only_available)
                else:
                    await turn_context.send_activity("You are already on the first page.")
            else:
                await turn_context.send_activity("No active search. Please start a new search.")
        
        else:
            logger.debug("Message didn't match any specific commands, treating as generic question")
            # Handle generic questions with OpenAI
            openai_response = await self.handle_generic_question(turn_context, message_text)
            
            logger.debug(f"OpenAI response successful: {openai_response}")
            
        # If OpenAI couldn't provide a meaningful response, fall back to the default message
            if not openai_response:
                logger.debug("Falling back to default response")
                response = "I'm not sure how to respond to that. Here are some things you can try:"
                response += "\n- Search for products: 'search for product [product name]'"
                response += "\n- Search for available products: 'search for available [product name]'"
                response += "\n- Get price and availability: 'price and availability for [part number]'"
                response += "\n- Navigate search results: 'next' or 'previous'"
                response += "\n- Or you can ask me general questions about computer hardware!"
                await turn_context.send_activity(response)
        # Remove this line to avoid printing the user's message
        # print(f"Sent response: {response}")  # Print to console for debugging

    async def search_product(self, turn_context: TurnContext, search_term: str, page_number: int, only_available: bool = False):
        logger.debug(f"Searching for product: {search_term}, page: {page_number}, only available: {only_available}")
        configuration = xi.sdk.resellers.Configuration(
            host="https://api.ingrammicro.com:443/sandbox"
        )

        try:
            await self.ensure_access_token()

            configuration.access_token = self.access_token

            search_term = search_term.replace("laptop", "Notebook")

            with xi.sdk.resellers.ApiClient(configuration) as api_client:
                api_instance = ProductCatalogApi(api_client)

                im_customer_number = '20-222222'  # Replace with your actual customer number
                im_correlation_id = str(uuid.uuid4())[:32]  # Truncate to 32 characters
                im_country_code = 'US'
                page_size = 10
                keyword = [search_term]

                api_response = api_instance.get_reseller_v6_productsearch(
                    im_customer_number=im_customer_number,
                    im_correlation_id=im_correlation_id,
                    im_country_code=im_country_code,
                    page_size=page_size,
                    page_number=page_number,
                    keyword=keyword
                )

                logger.debug(f"API response received: {api_response}")

                if api_response.catalog and len(api_response.catalog) > 0:
                    # Prepare a list of products for batch request
                    product_list = [PriceAndAvailabilityRequestProductsInner(ingram_part_number=product.ingram_part_number) 
                                    for product in api_response.catalog[:10]]

                    # Make a single batch request for price and availability
                    p_and_a_request = PriceAndAvailabilityRequest(products=product_list)
                    p_and_a_response = api_instance.post_priceandavailability(
                        im_customer_number=im_customer_number,
                        im_correlation_id=im_correlation_id,
                        im_country_code=im_country_code,
                        include_availability=True,
                        include_pricing=True,
                        price_and_availability_request=p_and_a_request
                    )

                    # Process the batch response
                    filtered_products = []
                    for product, p_and_a_info in zip(api_response.catalog[:10], p_and_a_response):
                        is_available = p_and_a_info.availability and p_and_a_info.availability.total_availability > 0
                        if not only_available or (only_available and is_available):
                            filtered_products.append((product, p_and_a_info))

                    if filtered_products:
                        response = f"Page {page_number} results for '{search_term}':\n\n"
                        for product, p_and_a_info in filtered_products:
                            response += f"**Name**: {product.description}  \n"
                            response += f"**Part Number**: {product.ingram_part_number}  \n"
                            response += f"**Vendor**: {product.vendor_name}  \n"
                            response += f"**Category**: {product.category}  \n"
                            response += f"**Sub-Category**: {product.sub_category}  \n"
                            response += f"**Product Type**: {product.product_type}  \n"
                            response += f"**UPC Code**: {product.upc_code}  \n"
                            response += f"**Availability**: {'Available' if p_and_a_info.availability and p_and_a_info.availability.total_availability > 0 else 'Not Available'}  \n"
                            if p_and_a_info.availability:
                                response += f"**Total Availability**: {p_and_a_info.availability.total_availability}  \n"
                            response += "  \n"

                        response += (f"\nPage {page_number}. "
                                    "To view the next page of results, type 'next'.  \n"
                                    "To view the previous page of results, type 'previous'.  \n"
                                    "To see price and availability details for a specific product, type 'price and availability for [part number]'.")
                    else:
                        response = f"No products found matching your criteria on page {page_number}."
                else:
                    response = f"No products found matching your search term on page {page_number}."

                await turn_context.send_activity(response)
                logger.info(f"Sent search results for '{search_term}'")

        except ApiException as e:
            error_message = f"An API error occurred: {str(e)}"
            logger.error(error_message)
            await turn_context.send_activity(error_message)

        except Exception as e:
            error_message = f"An unexpected error occurred: {str(e)}"
            logger.error(error_message)
            await turn_context.send_activity(error_message)

    async def get_price_and_availability(self, turn_context: TurnContext, part_number: str):
        logger.debug(f"Getting price and availability for part number: {part_number}")
        configuration = xi.sdk.resellers.Configuration(
            host="https://api.ingrammicro.com:443/sandbox"
        )

        try:
            await self.ensure_access_token()

            configuration.access_token = self.access_token

            with xi.sdk.resellers.ApiClient(configuration) as api_client:
                api_instance = ProductCatalogApi(api_client)

                im_customer_number = '20-222222'  # Replace with your actual customer number
                im_correlation_id = str(uuid.uuid4())[:32]  # Truncate to 32 characters
                im_country_code = 'US'

                # Get price and availability
                products = [PriceAndAvailabilityRequestProductsInner(ingram_part_number=part_number)]  # Use the original part_number here
                price_and_availability_request = PriceAndAvailabilityRequest(products=products)

                api_response = api_instance.post_priceandavailability(
                    im_customer_number=im_customer_number,
                    im_correlation_id=im_correlation_id,
                    im_country_code=im_country_code,
                    include_availability=True,
                    include_pricing=True,
                    price_and_availability_request=price_and_availability_request
                )

                logger.debug(f"API response received: {api_response}")

                if api_response and len(api_response) > 0:
                    product_info = api_response[0]
                    
                    response = f"**Name**: {product_info.description or 'N/A'}  \n"
                    response += f"**Ingram Part Number**: {product_info.ingram_part_number}  \n"
                    response += f"**Vendor Part Number**: {product_info.vendor_part_number or 'N/A'}  \n"
                    
                    if product_info.availability:
                        total_availability = product_info.availability.total_availability
                        response += f"**Availability**: {'Available' if total_availability > 0 else 'Not Available'}  \n"
                        response += f"**Total Availability**: {total_availability}  \n"
                        
                        availability_by_warehouse = product_info.availability.availability_by_warehouse or []
                        available_warehouses = [
                            f"**Warehouse**: {wh.location if hasattr(wh, 'location') else 'N/A'}, "
                            f"**Quantity Available**: {wh.quantity_available}"
                            for wh in availability_by_warehouse
                            if hasattr(wh, 'quantity_available') and wh.quantity_available > 0
                        ]
                        
                        if available_warehouses:
                            response += "**Availability by Warehouse**:  \n" + "  \n".join(available_warehouses) + "  \n"
                        else:
                            response += "**No warehouses with available stock**.  \n"
                    
                    if product_info.pricing:
                        response += f"**Pricing (Currency {product_info.pricing.currency_code or 'N/A'})**:  \n"
                        if hasattr(product_info.pricing, 'retail_price'):
                            retail_price = product_info.pricing.retail_price
                            response += f"**Retail Price**: ${retail_price:.2f}  \n" if retail_price is not None else "Retail Price: N/A  \n"
                        if hasattr(product_info.pricing, 'customer_price'):
                            customer_price = product_info.pricing.customer_price
                            response += f"**Customer Price**: ${customer_price:.2f}  \n" if customer_price is not None else "Customer Price: N/A  \n"
                else:
                    response = f"**No price and availability information found for part number {part_number}**."

                await turn_context.send_activity(response)
                print(f"Sent price and availability for '{part_number}'")  # Print to console for debugging

        except ApiException as e:
            error_message = f"An API error occurred: {str(e)}"
            logger.error(error_message)
            await turn_context.send_activity(error_message)

        except Exception as e:
            error_message = f"An unexpected error occurred: {str(e)}"
            logger.error(error_message)
            await turn_context.send_activity(error_message)

    async def search_excel_products(self, turn_context: TurnContext, search_term: str):
        if self.excel_data is None:
            await self.load_excel_data()
        
        if self.excel_data is not None:
            results = self.excel_api.search_products(self.excel_data, search_term)
            if not results.empty:
                formatted_results = self.excel_api.format_results(results)
                await turn_context.send_activity(f"Search results for '{search_term}':\n\n{formatted_results}")
            else:
                await turn_context.send_activity(f"No products found matching '{search_term}' in the Excel file.")
        else:
            await turn_context.send_activity("Sorry, I couldn't access the Excel data. Please try again later.")
        
        # Add this line to prevent further processing
        return True  # Indicate that the message has been handled

    async def on_members_added_activity(
        self, members_added: [ChannelAccount], turn_context: TurnContext
    ):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    "Hello! I'm Apollobot.  \nI am here to help you search for products in Ingram Micro, and the Aera Procure database, or just reply on generic questions about computer software and hardware.  \n"
                    "Just type '**search for product**' followed by your search term for Ingram Micro database search,  \nor '**search for available**' followed by your search term for Ingram Micro database available products,  \n"
                    "'**excel search for**' followed by your search term for Aera Procure file search,  \n"
                    "or ask me anything!"
                )
