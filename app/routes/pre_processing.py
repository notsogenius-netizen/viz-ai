import httpx
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas import ExternalDBCreateRequest, ExternalDBResponse, CurrentUser, UpdateDBRequest,ExternalDBCreateChatRequest
from app.services.pre_processing import create_or_update_external_db, update_record, post_to_llm, save_query_to_db
from app.services.pre_processing import process_nl_to_sql_query,post_to_nlq_llm,save_nl_sql_query
from app.utils.auth_dependencies import get_current_user
from app.core.db import get_db

router = APIRouter(prefix="/external-db", tags=["External Database"])

@router.post("/", response_model=ExternalDBResponse, status_code=status.HTTP_201_CREATED)
async def create_external_db(data: ExternalDBCreateRequest, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    """
    API to connect to an external database, retrieve schema, and store it in the internal database.
    """
    return await create_or_update_external_db(data, db, current_user)


@router.patch("/", status_code=status.HTTP_202_ACCEPTED)
async def update_record_and_call_llm(data: UpdateDBRequest, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    """
    API to update external db model and call llm service for processing.
    """
    url = "http://192.168.94.213:8001/queries/"

    saved_data = await update_record(data, db, current_user)
    llm_response = await post_to_llm(url, saved_data)
    # llm_response = [
    #     {
    #         "query": "SELECT pl.productLine, DATE_TRUNC('month', o.orderDate) AS month, SUM(od.quantityOrdered * od.priceEach) AS monthly_revenue FROM productlines pl JOIN products p ON pl.productLine = p.productLine JOIN orderdetails od ON p.productCode = od.productCode JOIN orders o ON od.orderNumber = o.orderNumber WHERE o.orderDate >= '[MIN_DATE]' AND o.orderDate <= '[MAX_DATE]' GROUP BY pl.productLine, month ORDER BY month",
    #         "explanation": "What is the monthly revenue trend for each product line?",
    #         "relevance": 0.9,
    #         "is_time_based": True,
    #         "chart_type": "Line"
    #     },
    #     {
    #         "query": "SELECT pl.productLine, DATE_TRUNC('quarter', o.orderDate) AS quarter, SUM(od.quantityOrdered * (od.priceEach - p.buyPrice)) AS quarterly_profit FROM productlines pl JOIN products p ON pl.productLine = p.productLine JOIN orderdetails od ON p.productCode = od.productCode JOIN orders o ON od.orderNumber = o.orderNumber WHERE o.orderDate >= '[MIN_DATE]' AND o.orderDate <= '[MAX_DATE]' GROUP BY pl.productLine, quarter ORDER BY quarter",
    #         "explanation": "What is the quarterly profit margin trend for each product line?",
    #         "relevance": 0.8,
    #         "is_time_based": True,
    #         "chart_type": "Area"
    #     },
    #     {
    #         "query": "WITH YearlyRevenue AS ( SELECT pl.productLine, EXTRACT(YEAR FROM o.orderDate) AS year, SUM(od.quantityOrdered * od.priceEach) AS yearly_revenue FROM productlines pl JOIN products p ON pl.productLine = p.productLine JOIN orderdetails od ON p.productCode = od.productCode JOIN orders o ON od.orderNumber = o.orderNumber WHERE o.orderDate >= '[MIN_DATE]' AND o.orderDate <= '[MAX_DATE]' GROUP BY pl.productLine, year ) SELECT yr1.productLine, yr1.year, yr1.yearly_revenue, (yr1.yearly_revenue - COALESCE(yr2.yearly_revenue, 0)) * 100.0 / NULLIF(yr2.yearly_revenue,0) AS yoy_growth FROM YearlyRevenue yr1 LEFT JOIN YearlyRevenue yr2 ON yr1.productLine = yr2.productLine AND yr1.year = yr2.year + 1 ORDER BY yr1.productLine, yr1.year",
    #         "explanation": "What is the year-over-year revenue growth for each product line?",
    #         "relevance": 0.9,
    #         "is_time_based": True,
    #         "chart_type": "Bar"
    #     },
    #     {
    #         "query": "SELECT DATE_TRUNC('month', orderDate) AS month, AVG(order_total) as average_order_value FROM ( SELECT orderNumber, orderDate, SUM(quantityOrdered * priceEach) AS order_total FROM orderdetails od JOIN orders o ON o.orderNumber = od.orderNumber GROUP BY orderNumber, orderDate) as order_totals WHERE orderDate >= '[MIN_DATE]' AND orderDate <= '[MAX_DATE]' GROUP BY month ORDER BY month",
    #         "explanation": "What is the monthly average order value trend?",
    #         "relevance": 0.7,
    #         "is_time_based": True,
    #         "chart_type": "Line"
    #     },
    #     {
    #         "query": "SELECT p.productVendor, DATE_TRUNC('quarter', o.orderDate) AS quarter, SUM(od.quantityOrdered) AS quarterly_sales_quantity FROM products p JOIN orderdetails od ON p.productCode = od.productCode JOIN orders o ON od.orderNumber = o.orderNumber WHERE o.orderDate >= '[MIN_DATE]' AND o.orderDate <= '[MAX_DATE]' GROUP BY p.productVendor, quarter ORDER BY quarter",
    #         "explanation": "What is the quarterly sales quantity trend for each product vendor?",
    #         "relevance": 0.7,
    #         "is_time_based": True,
    #         "chart_type": "Area"
    #     },
    #     {
    #         "query": "SELECT pl.productLine, SUM(od.quantityOrdered * od.priceEach) AS total_revenue FROM productlines pl JOIN products p ON pl.productLine = p.productLine JOIN orderdetails od ON p.productCode = od.productCode GROUP BY pl.productLine",
    #         "explanation": "What is the product revenue distribution across different product lines?",
    #         "relevance": 0.8,
    #         "is_time_based": False,
    #         "chart_type": "Pie"
    #     },
    #     {
    #         "query": "SELECT p.productName, AVG(od.priceEach - p.buyPrice) AS avg_profit_margin FROM products p JOIN orderdetails od ON p.productCode = od.productCode GROUP BY p.productName",
    #         "explanation": "What is the average profit margin for each product?",
    #         "relevance": 0.9,
    #         "is_time_based": False,
    #         "chart_type": "Bar"
    #     },
    #     {
    #         "query": "SELECT p.productLine,p.buyPrice, p.MSRP FROM products p",
    #         "explanation": "What is the correlation between buy price and MSRP for each product line?",
    #         "relevance": 0.6,
    #         "is_time_based": False,
    #         "chart_type": "Scatterplot"
    #     },
    #     {
    #         "query": "SELECT p.productName, p.quantityInStock, SUM(od.quantityOrdered) AS total_quantity_ordered, p.quantityInStock/SUM(od.quantityOrdered) AS ratio FROM products p LEFT JOIN orderdetails od ON p.productCode = od.productCode GROUP BY p.productName, p.quantityInStock",
    #         "explanation": "What is the ratio of quantity in stock to quantity ordered for each product?",
    #         "relevance": 0.7,
    #         "is_time_based": False,
    #         "chart_type": "Bar"
    #     },
    #     {
    #         "query": "SELECT e.firstName, e.lastName, SUM(od.quantityOrdered * od.priceEach) AS total_revenue FROM employees e JOIN customers c ON e.employeeNumber = c.salesRepEmployeeNumber JOIN orders o ON c.customerNumber = o.customerNumber JOIN orderdetails od ON o.orderNumber = od.orderNumber GROUP BY e.firstName, e.lastName",
    #         "explanation": "What is the total revenue generated by each sales representative?",
    #         "relevance": 0.6,
    #         "is_time_based": False,
    #         "chart_type": "Donut"
    #     }
    # ]
    # print(data.db_entry_id)
    response = await save_query_to_db(queries=llm_response, db= db, db_entry_id= data.db_entry_id)
    return response

# @router.post("/test")
# async def test_route(data: dict):
#     url = "http://192.168.1.21:8001/queries/"
#     try:
#         llm_response = await post_to_llm(url, data)
#         return {"status": "success", "queries": llm_response}
#     except httpx.HTTPStatusError as e:
#         return {"status": "error", "message": str(e)}

logger = logging.getLogger(__name__)
@router.post("/nl-to-sql", status_code=status.HTTP_200_OK)
async def convert_nl_to_sql(data: ExternalDBCreateChatRequest, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
        url = "http://192.168.94.213:8001/api/nlq/convert_nl_to_sql"
        try:
              
            logger.info("Received NL query: %s", data.nl_query)

            nlq_data, db_entry_id = await process_nl_to_sql_query(data, db, current_user)
            logger.info("Processed NL to SQL Query, Data: %s, DB Entry ID: %s", nlq_data, db_entry_id)

            sql_response = await post_to_nlq_llm(url, nlq_data)
            logger.info("Received SQL response: %s", sql_response)

            save_result = await save_nl_sql_query(sql_response, db, db_entry_id)        
            logger.info("Save result: %s", save_result)

            return {
                "status": "success",
                "sql_query": sql_response,
                "save_status": save_result
            }

        except httpx.HTTPStatusError as e:
            logger.error("Error from NL to SQL service: %s", str(e))
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error from NL to SQL service: {str(e)}"
            )
    
        except HTTPException as e:
            logger.error("HTTP Exception: %s", str(e))
            raise e

        except Exception as e:
            logger.error("Unexpected Error processing NL to SQL request: %s", str(e), exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing NL to SQL request: {str(e)}"
            )