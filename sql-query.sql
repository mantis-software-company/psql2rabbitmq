SELECT
    pa.paper_id as id, pa.title, pa.abstract_content as abstract, pa.start_page_number as "startPage", pa.end_page_number as "endPage", pa.citation_count, pa.control_date, upper(pa."language") as "language"
    ,jy.issocial, jy.isscience, j.journal_id as "journalCode",j."name" as "journalName", j.web_address as "journalWebAddress", pa.pdf_path, pa.createdby_name as "createdBy", pa.doi as "publicationNumber", j.issn, j.e_issn 	
    ,case paper_access.access_status when 'OPEN' then DATE('1970-01-01') else DATE('2100-01-01') end "accessibleDate"
    ,(select jsonb_agg(distinct su.subject_name) from paper_subject_heading_relation as pshr left join subjects_mw as su on su.id = pshr.subject_heading_id where pshr.paper_id = pa.paper_id) subjects
    ,par.par_json as author_json
    ,(select jsonb_agg(json_build_object(
        'id',r.reference_id,
        'orderNumber',r.reference_order, 
        'referenceText',REGEXP_REPLACE(r.reference_full_text,'([^\w\s''])*','','g'))) from reference r where r.source_paper =pa.paper_id)  as references_json
    ,paper_other_context.languageContext_json
    ,json_build_object(
        'id',ji.journal_issue_id,
        'volume',ji.volume, 
        'number',ji.number, 
        'isSpecial',ji.special_issue, 
        'year',jy.year, 
        'publishDate', DATE('"' || jy.year || '-' || ji.month || '-01"'), 
        'period',ji.month) as issue_json  	
FROM paper pa
    inner join journal_issue as ji on ji.journal_issue_id = pa.journal_issue 
    inner join journal_year as jy on jy.journal_year_id = ji.journal_year
    inner join journal as j on j.journal_id = jy.journal
    left join paper_author_mw par on par.paper_id=pa.paper_id
    left join paper_abstract_language_mw as paper_other_context on paper_other_context.paper_id = pa.paper_id
    left join paper_full_text_access as paper_access on paper_access.paper_id = pa.paper_id
order by pa.paper_id