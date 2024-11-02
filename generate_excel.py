import pandas as pd
from io import BytesIO

def generate_excel(dataframe):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        dataframe.to_excel(writer, sheet_name="Planilha", index=False)
    output.seek(0)
    return output