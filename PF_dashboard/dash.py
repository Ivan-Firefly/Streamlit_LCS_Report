import streamlit as st
import json
import csv
import os
import pandas as pd
import s3fs
import numpy as np
import xlsxwriter
import io
from PIL import Image
import plotly.express as px
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode, ColumnsAutoSizeMode
from pyxlsb import open_workbook as open_xlsb
from streamlit_extras.customize_running import center_running
import time
from datetime import datetime

#from io import BytesIO

image = Image.open('nVent_Logo_RGB_rev_F2.png')
new_image = image.resize((150, 100))
icon_img = Image.open('nVent_Icon_Red.png')
st.set_page_config(layout="wide",page_title="PF Dashboard",page_icon = icon_img)

# image = Image.open('nVent_Logo_RGB_rev_F2.png')
# new_image = image.resize((150, 100))

hide_default_format = """
       <style>
       #MainMenu {visibility: hidden; }
       footer {visibility: hidden;}
       </style>
       """

remove_white_spaces = """
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
        </style>
        """

st.markdown(hide_default_format, unsafe_allow_html=True)
st.markdown(remove_white_spaces, unsafe_allow_html=True)


fs = s3fs.S3FileSystem(anon=False)

@st.cache_data(ttl=9800)
def list_files(search_item):
    return fs.find(search_item)

@st.cache_data(ttl=9800)
def read_file(filename):
    with fs.open(filename) as f:
        return f.read().decode("utf-8")


#st.image('nVent_Logo_RGB_rev_F2.png')


#st.image(new_image)

#nvent_logo = st.file_uploader('nVent_Logo_RGB_rev_F2.png', type='png', key=6)
#if nvent_logo is not None:
#    image = Image.open(nvent_logo)
#    new_image = image.resize((600, 400))
#    st.image(new_image)
col_h1, col_h2 = st.columns([1,3])

with col_h1:
    st.image(new_image)

with col_h2:
    st.markdown("""
            # ProntoForms Audits Dashboard
            """)

        #  Welcome 👋 \n
        # Download data collected with ProntoForms on Audit and Construction Projects.

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        col_pass1, col_pass2, col_pass3 = st.columns([1,3,1])
        with col_pass2:
            st.text_input(
                "Password", type="password", on_change=password_entered, key="password"
            )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        col_pass1, col_pass2, col_pass3 = st.columns([1,3,1])
        with col_pass2:
            st.text_input(
                "Password", type="password", on_change=password_entered, key="password"
            )
        col_passerr1, col_passerr2, col_passerr3 = st.columns([1,3,1])
        with col_passerr2:
            st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

if check_password():

    with st.sidebar.expander("ABOUT THE DASHBOARD"):
        st.markdown("""
                Dashboard visualizes core information related to TrueContext(ProntoForms) usage.
                \n"Collect Data" button runs a query retrieving values from forms submitted during
                Circuit(NF373), Insulation(NF374) or Panel(NF375) audits.
                By default, each refresh is stored for 60 min.
                \nFor improved legibility please:
                    \n- hide this sidebar menu
                    \n- hover over graphs to see tooltips with corresponding data
                    \n- use legends in right-hand side upper corners to filter out categories
                    \n- use graph menu bar appearing above them to resize, scale or download
                """)

    @st.cache_data(ttl=9800)
    def get_csvsource(file_name):
        file_content = read_file(file_name)
        data = pd.read_csv(io.StringIO(file_content))
        return data

    @st.cache_data(ttl=3600)
    def collect_data():

        searched_dir = 's3-nvent-prontoforms-data/Audits/'
        list_of_files = list_files(searched_dir)
        searched_files = []

        form_df = None

        for s3_file in list_of_files:
            if s3_file.split('.')[-1] == 'json':
                searched_files.append(s3_file)

        farea = []
        fcountry = []
        fstatus = []
        fname = []
        fuser = []
        fscope= []
        fdate = []
        fproj = []

        for jejson in searched_files:

            file_content = read_file(jejson)
            data = json.loads(file_content)

            farea.append(data['zone'])
            fstatus.append(data['state'])
            fname.append(data['form']['name'])
            fuser.append(data['user']['displayName'].split(' (')[0])
            try:
                #geostamp = data['geoStamp']['success']
                if data['geoStamp']['success']==True:
                    fcountry.append(data['geoStamp']['address'].split(', ')[-1])
                else:
                    fcountry.append('N/A')
            except:
                fcountry.append('N/A')
            # else:
            #     if data['geoStamp']['success']==True:
            #         fcountry.append(data['geoStamp']['address'].split(', ')[-1])
            #     else:
            #         fcountry.append('N/A')
            fdate.append(data['deviceSubmitDate']['provided']['time'][:10])

            fscope_cnt = 0
            fproj_cnt = 0
            
            for item in data['pages'][0]['sections']:
                if item['type'] == 'Flow':
                    for answer in item['answers']:
                        if answer['label'] == 'AuditScope':
                            fscope.append(answer['values'][0])
                            fscope_cnt+=1
                            #print(answer['values'][0])
                        if answer['label'] == 'nvt_ProjectNo':
                            fproj.append(answer['values'][0])
                            fproj_cnt+=1
                            
            if fscope_cnt == 0:
                fscope.append('N/A')
            if fproj_cnt == 0:
                fproj.append('N/A')      


        raw_rep_df = pd.DataFrame({'Zone':farea,'Geoloc':fcountry,'Status':fstatus,'Project':fproj,'User':fuser,
                        'Form':fname,'Scope':fscope,'Date':fdate})

        dummies = ['Dirk Meulemans','Kamila Czepiel','Pawel Czepiel']
        dummy_proj = ['P.BE123456','P.NL123456','P.NL230035','P.GB240999']


        audit_rep_df = raw_rep_df[~raw_rep_df.User.isin(dummies)]
        audit_rep_df = audit_rep_df[~audit_rep_df.Project.isin(dummy_proj)]
        audit_rep_df['Proj_country'] = audit_rep_df['Project'].apply(lambda x: x[2:4])
        audit_rep_df['Form_code'] = audit_rep_df['Form'].apply(lambda x: x[:5])

        def language_check(x):
            lang = x.split(' ')[0]
            if lang == 'Level':
                x_lang = 'EN'
            elif lang == 'Stufe':
                x_lang = 'DE'
            elif lang == 'Niveau':
                x_lang = 'FR'
            else:
                x_lang = 'EN'
            return x_lang

        def level_check(x):
            # if x != 'N/A':
            #     lvl = x.split(' ')[1]
                
            # else:
            #     lvl = '3'
            # return lvl
        
            if x == 'N/A':
                lvl = 'Level 3'
            else:
                if 'Stufe' in x:
                    lvl = x.replace('Stufe','Level')
                elif 'Niveau' in x:
                    lvl = x.replace('Niveau','Level')
                else:
                    lvl = x
            return lvl

        audit_rep_df['Language'] = audit_rep_df['Scope'].apply(language_check)
        audit_rep_df['Year_Month'] = audit_rep_df['Date'].apply(lambda x: x[:7])

        audit_rep_df['Audit_level'] = audit_rep_df['Scope'].apply(level_check)


        return audit_rep_df

    def create_aggrid(df):
        gb_form_df = GridOptionsBuilder.from_dataframe(df)
        gb_form_df.configure_default_column(enablePivot=True, enableValue=True, enableRowGroup=True) # , groupable=True, editable=True
        gb_form_df.configure_selection(
            selection_mode='mulitple',use_checkbox=False,groupSelectsChildren="Group checkbox select children") #Enable multi-row selection
        gb_form_df.configure_side_bar()                
        gridOptions_form_df = gb_form_df.build()

        grid_return_form_df = AgGrid(
            df,
            gridOptions=gridOptions_form_df,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED, 
            update_mode = GridUpdateMode.VALUE_CHANGED | GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.FILTERING_CHANGED | GridUpdateMode.SORTING_CHANGED,
            fit_columns_on_grid_load=False,
            theme='streamlit',
            enable_enterprise_modules=True,
            height=350, 
            width='100%',
            reload_data=True,
            columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
        )

        return grid_return_form_df

    def to_excel(df):
        output = io.BytesIO()
        # workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        # worksheet = workbook.add_worksheet()
        # worksheet.write('A1', 'Hello')
        # workbook.close()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        #tab_name = form_select.split('-')[0]
        df.to_excel(writer, index=False, sheet_name='audit_projects')
        workbook = writer.book
        worksheet = writer.sheets['audit_projects']
        format1 = workbook.add_format({'num_format': '0.00'}) 
        worksheet.set_column('A:A', None, format1)  
        writer.close()
        processed_data = output.getvalue()
        return processed_data    

    with st.form('input'):

        with st.sidebar:

            submit_button = st.form_submit_button('Collect Data')

            st.markdown("""
            ### :red[Legend:]
            """) 
            st.write('NF373 - EHT Circuit Audit')
            st.write('NF374 - EHT Insulation Audit')
            st.write('NF375 - EHT Panel Audit')
            st.write(' ')
            st.write('Level 1 - Basic')
            st.write('Level 2 - Standard')
            st.write('Level 3 - Advanced')
        
        if submit_button:
            center_running()
            time.sleep(2)

            form_df = collect_data()
            projects_df = get_csvsource('s3-nvent-prontoforms-data/Data_sources/SAP_projects_all.csv')
            form_df = pd.merge(form_df, projects_df, how='left', left_on='Project', right_on= 'Project Definition')
            form_df.drop(columns=['Project Definition','Dropdown'],inplace=True)
            form_df.rename(columns={'Project Definition description':'Project Name'},inplace=True)

            # for sp in sales_proj:
            #     form_df.loc[form_df.Project==sp,''] = 

            #gb_form_df = create_aggrid(form_df)
            #selected = gb_form_df['selected_rows']
            #gb_form_df_data = gb_form_df['data']
            #st.table(gb_form_df_data)
            # gb_form_df = GridOptionsBuilder.from_dataframe(form_df)
            # gb_form_df.configure_default_column(enablePivot=True, enableValue=True, enableRowGroup=True) # , groupable=True, editable=True
            # gb_form_df.configure_selection(
            #     selection_mode='mulitple',use_checkbox=False,groupSelectsChildren="Group checkbox select children") #Enable multi-row selection
            # gb_form_df.configure_side_bar()
            # #gb_form_df.configure_pagination(paginationAutoPageSize=True)
            # #paginationAutoPageSize=True,
            # gridOptions_form_df = gb_form_df.build()
            # #gridOptions_form_df['suppressHorizontalScroll'] = False

            # grid_return_form_df = AgGrid(
            #     form_df,
            #     gridOptions=gridOptions_form_df,
            #     data_return_mode=DataReturnMode.FILTERED_AND_SORTED, 
            #     update_mode = GridUpdateMode.VALUE_CHANGED | GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.FILTERING_CHANGED | GridUpdateMode.SORTING_CHANGED,
            #     fit_columns_on_grid_load=False,
            #     theme='streamlit',
            #     enable_enterprise_modules=True,
            #     height=350, 
            #     width='100%',
            #     reload_data=True,
            #     columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS
            # )
            # gb_form_df_data = grid_return_form_df['data']
            

            #Projects, Countries, Form Types, Forms, Languages, #1 Language, #1 Level
            st.markdown("""
                    ### :red[Metrics]
                    """)  

            form_df_len = len(form_df)
            lang_mode = form_df['Language'].mode().tolist()[0]
            form_df_len_lm = len(form_df[form_df.Language==lang_mode])
            lm_part = int(round((form_df_len_lm/form_df_len)*100,0))
            lvl_mode = form_df['Audit_level'].mode().tolist()[0]
            form_df_len_sm = len(form_df[form_df['Audit_level']==lvl_mode])
            ls_part = int(round((form_df_len_sm/form_df_len)*100,0))

            form_mode = form_df['Form_code'].mode().tolist()[0]
            form_df_len_fm = len(form_df[form_df['Form_code']==form_mode])
            lf_part = int(round((form_df_len_fm/form_df_len)*100,0))
            #metric_col1, metric_col2, metric_col3, metric_col4, metric_col5, metric_col6, metric_col7 = st.columns(7)
            metric_col1, metric_col2, metric_col3, metric_col4, metric_col5, metric_col6, metric_col7, metric_col8 = st.columns([1,1,1,1,1,2,2,2])
            metric_col1.metric('# Projects',form_df['Project'].nunique())
            metric_col2.metric('# Countries',form_df['Proj_country'].nunique())
            metric_col3.metric('# Form Types',form_df['Form'].nunique())
            metric_col4.metric('# Forms',len(form_df))
            metric_col5.metric('# Languages', form_df['Language'].nunique())
            metric_col6.metric( '#1 Form', f'{form_mode}({lf_part}%)')            
            metric_col7.metric( '#1 Language', f'{lang_mode}({lm_part}%)')
            #metric_col6.metric( '#1 Language', f'{lang_mode}')
            #metric_col6.metric(f'({lm_part}%)')
            metric_col8.metric( '#1 Level', f'{lvl_mode}({ls_part}%)')
            ### HERE DFs for new graphs ###
  
            # DF - forms per year/month bar
            form_yearmonth_df = form_df.groupby('Year_Month').count().reset_index()
            form_yearmonth_df = form_yearmonth_df.rename(columns={'Zone':'Forms_count'})

            # DF - scatter project / year_month / forms_count
            form_df_df_scat = form_df.groupby(['Project','Project Name','Year_Month','Form_code']).count().reset_index()
            form_df_df_scat = form_df_df_scat.rename(columns={'Zone':'Forms_count'}) 



            # DF - projects per year/month
            proj_yearmonth_df = form_df.groupby(['Year_Month','Project']).count().groupby('Year_Month').count().reset_index()
            proj_yearmonth_df = proj_yearmonth_df.rename(columns={'Zone':'Forms_count'})            

            # DF - users projects
            user_proj_df = form_df.groupby(['User','Project','Project Name','Form_code']).count().reset_index()
            user_proj_df = user_proj_df.rename(columns={'Zone':'Forms_count'})

            #user_formcount_df = user_proj_df.groupby('User').sum().reset_index()
            user_formcount_df = user_proj_df.groupby(['User','Form_code']).sum().reset_index()
            #user_projcount_df = user_proj_df.groupby(['User','Project']).count().groupby('User').count().reset_index()

            # DF - country, form, level

            cfl_form_df = form_df.groupby(['Proj_country','Form_code','Audit_level','Language']).count().reset_index()
            cfl_form_df = cfl_form_df.rename(columns={'Zone':'Forms_count'})

            country_prj_df = form_df.groupby(['Project','Project Name','Proj_country','Form_code']).count().reset_index()
            country_prj_df = country_prj_df.rename(columns={'Zone':'Projects_count'})
            country_prj_df = country_prj_df.groupby(['Project','Project Name','Proj_country','Form_code']).count().reset_index()

            country_df = cfl_form_df.groupby(['Proj_country','Language']).sum().reset_index()

            customer_df = form_df.groupby(['CUSTOMER','Project','Project Name','Form_code']).count().reset_index()
            customer_df = customer_df.rename(columns={'Zone':'Forms_count'})
            customer_formcount_df = customer_df.groupby(['CUSTOMER','Form_code']).sum().reset_index()

            st.markdown("""
                    ### :red[Time Dimension]
                    """)       

            col_11, col_12, col_13 = st.columns([1,1,2])

            with col_11:
                fig11 = px.bar(form_yearmonth_df, x='Year_Month', y='Forms_count',title = "Submitted Forms",
                        labels={
                        "Year_Month": "Date",
                        "Forms_count": "Submitted Forms"
                        }).update_layout(
                    xaxis_title="Date", yaxis_title="Forms count")
                st.plotly_chart(fig11,use_container_width=True)

            with col_12:
                fig12 = px.bar(proj_yearmonth_df, x='Year_Month', y='Forms_count',title = "Projects in Audit",
                        labels={
                        "Year_Month": "Date",
                        "Forms_count": "Submitted Forms"
                        }).update_layout(
                    xaxis_title="Date", yaxis_title="Projects count")
                st.plotly_chart(fig12,use_container_width=True)

            with col_13:
                fig13 = px.scatter(form_df_df_scat, x="Year_Month", y="Project", color="Form_code", size='Forms_count',
                template='gridon', title = "Projects & Scope",hover_data=["Project Name"],
                labels={
                        "Year_Month": "Date",
                        "Project": "Projects",
                        "Form_code": "Form type"
                 })
                # .update_layout(
                #     xaxis_title="Date", yaxis_title="Projects")
                st.plotly_chart(fig13,use_container_width=True)

            st.markdown("""
                    ### :red[Supervisor Dimension]
                    """)  

            col_21, col_22, col_23 = st.columns([1,1,1])

            with col_21:
                fig21 = px.bar(user_formcount_df, x='User', y='Forms_count',title = "Forms & Scope",color='Form_code',
                        labels={
                        "User": "Supervisor",
                        "Forms_count": "Submitted Forms",
                        "Form_code": "Form type"
                 })                           
                st.plotly_chart(fig21,use_container_width=True)

            with col_22:
                # fig22 = px.bar(user_proj_df, x='User', y='Forms_count',title = "Audited Projects").update_layout(
                #     xaxis_title="Supervisor", yaxis_title="Projects count")
                fig22 = px.bar(user_proj_df, x='User', y='Forms_count',title = "Forms & Projects",color='Project',
                               hover_data={'Project':True,'Project Name':True,'Form_code':True,'Forms_count':True,'User':True},
                                labels={
                                "User": "Supervisor",
                                "Forms_count": "Submitted Forms",
                                "Form_code": "Form type"
                                }).update_layout(
                    xaxis_title="Supervisor", yaxis_title="Projects count")
                st.plotly_chart(fig22,use_container_width=True)

            with col_23:
                fig4 = px.scatter(user_proj_df, x="User", y="Project", color="Form_code", size='Forms_count',
                template='gridon', title = "Projects & Scope",hover_data=["Project Name"],
                labels={
                        "User": "Supervisor",
                        "Project": "Projects",
                        "Form_code": "Form type",
                        "Forms_count": "Submitted Forms"
                 })                
                # .update_layout(
                #     xaxis_title="Supervisor", yaxis_title="Projects")
                st.plotly_chart(fig4,use_container_width=True)


            st.markdown("""
                    ### :red[Country Dimension]
                    """)  

            #st.table(country_prj_df)
            col_31, col_32, col_33 = st.columns([1,1,1])

            with col_31:
                fig31 = px.bar(country_df, x='Proj_country', y='Forms_count',title = "Submitted Forms",color='Language',
                        hover_data=['Form_code'],
                        labels={
                        "Proj_country": "Country",
                        "Form_code": "Form type",
                        "Forms_count": "Submitted Forms"
                        }).update_layout(
                    xaxis_title="Country", yaxis_title="Forms count")
                st.plotly_chart(fig31,use_container_width=True)

            with col_32:
                fig32 = px.scatter(cfl_form_df, x="Proj_country", y="Form_code", color="Audit_level", size='Forms_count',
                template='gridon', title = "Scope & Level",
                labels={
                        "Proj_country": "Country",
                        "Form_code": "Form type",
                        "Audit_level": "Audit level",
                        "Forms_count": "Submitted Forms"
                 })
                # .update_layout(
                #     xaxis_title="Country", yaxis_title="Projects")
                st.plotly_chart(fig32,use_container_width=True)

            #country_prj_df = form_df.groupby(['Project','Project Name','Proj_country','Form_code']).count().reset_index()
            #hover_data=["Project","Project Name","Form_code"]
            with col_33:
                fig33 = px.bar(country_prj_df, x='Proj_country', y='Projects_count',title = "Audited Projects",color='Project',
                               hover_data={'Project':True,'Project Name':True,'Proj_country':False,'Form_code':True,'Projects_count':False},
                                labels={"Form_code": "Form type"}).update_layout(
                    xaxis_title="Country", yaxis_title="Projects count")
                st.plotly_chart(fig33,use_container_width=True)

            st.markdown("""
                    ### :red[Customer Dimension]
                    """)

            col_41, col_42, col_43 = st.columns([1,1,1])

            # customer_df = form_df.groupby(['CUSTOMER','Project','Form_code']).count().reset_index()
            # customer_formcount_df = customer_df.groupby(['CUSTOMER','Form_code']).sum().reset_index()


            with col_41:
                fig41 = px.bar(customer_formcount_df, x='CUSTOMER', y='Forms_count',title = "Forms & Scope",color='Form_code',
                        labels={
                        "CUSTOMER": "Customer",
                        "Forms_count": "Submitted Forms",
                        "Form_code": "Form type"
                 })                           
                st.plotly_chart(fig41,use_container_width=True)

            with col_42:
                fig42 = px.bar(customer_df, x='CUSTOMER', y='Forms_count',title = "Forms & Projects",color='Project',
                                hover_data=["Project Name","Form_code"],
                                labels={
                                "CUSTOMER": "Customer",
                                "Forms_count": "Submitted Forms",
                                "Form_code": "Form type"
                                }).update_layout(
                    xaxis_title="Customer", yaxis_title="Projects count"
                    )
                st.plotly_chart(fig42,use_container_width=True)

            with col_43:
                fig43 = px.scatter(customer_df, x="CUSTOMER", y="Project", color="Form_code", size='Forms_count',
                template='gridon', title = "Projects & Scope",hover_data=["Project Name"],
                labels={
                        "CUSTOMER": "Customer",
                        "Project": "Projects",
                        "Form_code": "Form type"
                 })                
                # .update_layout(
                #     xaxis_title="Supervisor", yaxis_title="Projects")
                st.plotly_chart(fig43,use_container_width=True)


            df_xlsx_mat = to_excel(form_df)
            st.sidebar.download_button(label='Download to EXCEL',
                                            data=df_xlsx_mat ,
                                            file_name= "audit_projects.xlsx"
                                            )
            #st.table(customer_df)

            # fault_df = gb_form_df_data[gb_form_df_data['Status']=='Fault']
            # fault_df = fault_df.groupby(['Project','Form','ID','Question_name','Question_subname']).agg({'Status':'count'}).reset_index()
            # fault_df.rename(columns={'Status':'Quantity'},inplace=True)
            # fault_df_graph = fault_df[['Project','Form','Question_name','Question_subname','Quantity']]
            # fault_df_graph.Question_name[fault_df_graph.Question_name=='Field Insulation Inspections'] = fault_df_graph.Question_subname
            # fault_df_graph = fault_df_graph.groupby(['Project','Form','Question_name','Question_subname']).agg({'Quantity':'sum'}).reset_index()

            # mat_df_type = gb_form_df_data[
            #     (gb_form_df_data['Section'].str.contains("_Material")) & (gb_form_df_data['Question_subname'].str.startswith("Required Material")) ]
            # mat_df_type = mat_df_type[mat_df_type['Answer']!=""]
            # mat_df_qty = gb_form_df_data[
            #     (gb_form_df_data['Section'].str.contains("_Material")) & (gb_form_df_data['Question_subname'].str.startswith("Quantity")) ]
            # mat_df_qty['Answer'] = mat_df_qty['Answer'].replace("",1)
            # mat_df_qty.rename(columns={'Answer':'Quantity'},inplace=True)             
            # mat_df_type.reset_index(inplace=True)
            # mat_df_type = pd.merge(mat_df_type, mat_df_qty, how='left', on=['Project','Form','ID','Section','Item','Question_name'])


            # mat_df_type['Quantity'] = mat_df_type['Quantity'].astype(int)
            # mat_df_type = mat_df_type.groupby(['Project','Form','Question_name','ID','Answer']).agg({'Quantity':'sum'}).reset_index()
            # mat_df_type.rename(columns={'Answer':'Material'},inplace=True)
            # mat_df_type_graph = mat_df_type.groupby(['Project','Form','Material']).agg({'Quantity':'sum'}).reset_index()
        
            # if len(fault_df)!=0:
            #     fig2 = px.scatter(fault_df_graph, x="Form", y='Question_name', color="Project", size='Quantity',
            #     template='gridon', title = "Reported Faults",
            #     #category_orders={'TaskName':task_list},
            #     height=500)
            #     st.plotly_chart(fig2,use_container_width=True)
            # else:
            #     st.write('NO FAULTS RECORDED')

            # if len(mat_df_type_graph)!=0:
            #     fig3 = px.scatter(mat_df_type_graph, x="Form", y="Material", color="Project", size='Quantity',
            #     template='gridon', title = "Reported Replacement Materials", 
            #     #category_orders={'TaskName':task_list},
            #     height=500)
            #     st.plotly_chart(fig3,use_container_width=True)
            # else:
            #     st.write('NO MATERIAL REPLACEMENTS PROPOSED')





