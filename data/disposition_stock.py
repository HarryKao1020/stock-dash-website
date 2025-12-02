
非處置股 = data.get('etl:disposal_stock_filter')
非注意股 = data.get('etl:noticed_stock_filter')
當前處置股=非處置股.iloc[-1][非處置股.iloc[-1]==False].index.tolist()
當前注意股=非注意股.iloc[-1][非注意股.iloc[-1]==False].index.tolist()

def get_stockid_companyname(stock_list):
    """
    根據給定的股票代碼列表，返回一個字典，字典的鍵是股票代碼，值是對應的公司簡稱。
    
    參數:
    stock_list (list): 股票代碼的列表。
    
    返回:
    dict: 股票代碼與公司簡稱的對應字典。
    """
    # 篩選出列表中的股票並轉成字典
    company_info = data.get('company_basic_info')

    # 篩選並同時保留 stock_id
    result = company_info.loc[company_info['stock_id'].isin(stock_list), ['stock_id', '公司簡稱']]

    # 將 stock_id 設為索引
    result_indexed = result.set_index('stock_id')['公司簡稱']

    # 按照 stock_list 的順序重新排列
    result_ordered = result_indexed.reindex(stock_list)

    # 轉成字典 (保持順序)
    stock_name_dict = result_ordered.to_dict()
    # print(stock_name_dict)
    return stock_name_dict

print(get_stockid_companyname(當前處置股))
print(get_stockid_companyname(當前注意股))
print(f'處置股數量: {len(當前處置股)}')
print(f'注意股數量: {len(當前注意股)}')

非處置股
    