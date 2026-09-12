import pandas as pd
from datetime import datetime, timedelta
import re

# Let's inspect all 25 samples
df_s = pd.read_csv('dataset/sample_requests.csv')
df_p = pd.read_csv('dataset/financial_profiles.csv').set_index('user_id')
df_e = pd.read_csv('dataset/financial_events.csv')
df_m = pd.read_csv('dataset/messages.csv')
df_r = pd.read_csv('dataset/request_payment_options.csv')

print(f"Total samples: {len(df_s)}")
