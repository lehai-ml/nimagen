""""
genes.py
perform gene/gene-set analysis

Following steps are available:
    SNPsFunctionalAnalysis
        extract_new_bed_file
        do_mass_univariate_test - perform mass univariate test on each SNP
        get_the_best_SNPs
        SNPs_annotation_to_gene
        
    
"""
from typing import List, DefaultDict, Union, Optional
import pandas as pd
import numpy as np
import bed_reader
import statsmodels.api as sm
from scipy.stats import hypergeom
from statsmodels.stats.multitest import fdrcorrection
from collections import defaultdict
import tqdm

class SNPsFunctionalAnalysis:
    """Functional analysis pipeline    
    """

    def __init__(self,
                 snps_list: Union[List[str], pd.DataFrame],
                 bed_file: Optional[Union[str, bed_reader.open_bed]] = None) -> None:
        """Initialise the pipeline

        Args:
            snps_list (Union[List[str], pd.DataFrame]): List of SNPs or a dataframe with a column named SNPs
            bed_file (Optional[Union[str, bed_reader.open_bed]], optional): The bed file containing the genetic information. Defaults to None.
        """
        if type(snps_list) == pd.DataFrame:
            self.snps_list = snps_list.SNP.to_list()

        self.updated_snps_list = False
        self.updated_bed_file = False
        if type(snps_list) == list:
            self.snps_list = snps_list
        if bed_file is not None:
            if type(bed_file) == str:
                self.orig_bed_file = bed_reader.open_bed(bed_file)
            else:
                assert type(bed_file) == bed_reader.open_bed
                self.orig_bed_file = bed_file

    @staticmethod
    def extract_new_bed_file(bed_file: Union[str, bed_reader.open_bed],
                         snps_list: Optional[List[str]] = None,
                         fid_list: Optional[Union[pd.DataFrame, str, List[str]]] = None) -> bed_reader.open_bed:
        
        """[Return a new bed_file object, with selected individual and selected genotyped data]

        Args:
            snps_list (Optional[List[str]]): [list of snps]
            fid_list (Optional[Union[pd.DataFrame, str, List[str]]]): [list of fid, can be either pd.Dataframe, and it will look for FID column, or path to the dataframe.]
            bed_file (Union[str, bed_reader.open_bed]): [the bed file, or path to the bed file]

        Returns:
            bed_reader.open_bed: [New bed file object with the necessary information for the SNPsFunctionalAnalysis pipeline]
        """
        if type(bed_file) == str:
            bed_file = bed_reader.open_bed(bed_file)
        else:
            assert type(bed_file) == bed_reader.open_bed
        if type(fid_list) == str:
            fid_list = pd.read_table(fid_list, sep=' ')
            fid_list = fid_list.FID.to_list()
        if type(fid_list) == pd.DataFrame:
            fid_list = fid_list.FID.to_list()

        # always when reading bed file assign the value to genotype attribute
        if not hasattr(bed_file, 'genotype'):
            bed_file.genotype = bed_file.read()
        if snps_list is not None:  # change the bed_file SNPs and associated
            new_sid = [idx for idx, sid in enumerate(
                bed_file.sid) if sid in snps_list]
            bed_file.genotype = bed_file.genotype[:, new_sid]
            # can change the properties dictionary but not the attributes
            bed_file.properties_dict['sid'] = bed_file.sid[new_sid]
            bed_file.properties_dict['chromosome'] = bed_file.chromosome[new_sid]
            bed_file.properties_dict['cm_position'] = bed_file.cm_position[new_sid]
            bed_file.properties_dict['bp_position'] = bed_file.bp_position[new_sid]
            bed_file.properties_dict['allele_1'] = bed_file.allele_1[new_sid]
            bed_file.properties_dict['allele_2'] = bed_file.allele_2[new_sid]

        if fid_list is not None:  # change the bed_file ID info
            temp_fid_list = [i.split('-')[0] for i in fid_list] #set anything in the fid as no '-' if there is '-' in the fid.
            new_fid = [idx for idx, i in enumerate(bed_file.fid) 
                       if (i.split('-')[0] in temp_fid_list)]
            bed_file.properties_dict['fid'] = bed_file.fid[new_fid]
            bed_file.properties_dict['iid'] = bed_file.iid[new_fid]
            bed_file.properties_dict['father'] = bed_file.father[new_fid]
            bed_file.properties_dict['mother'] = bed_file.mother[new_fid]
            bed_file.properties_dict['sex'] = bed_file.sex[new_fid]
            bed_file.properties_dict['pheno'] = bed_file.pheno[new_fid]
            bed_file.genotype = bed_file.genotype[new_fid, :]
            
        return bed_file

    @staticmethod
    def do_mass_univariate_test(orig_bed_file: Union[str, bed_reader.open_bed],
                         pheno_file: Optional[Union[str, pd.DataFrame]] = None,
                         covar_file: Optional[Union[str, pd.DataFrame]] = None,
                         pheno_covar_file: Optional[Union[str,
                                                          pd.DataFrame]] = None,
                         snps_list: Optional[List[str]] = None,
                         phenotype: str = None,
                         updated_bed_file:Optional[Union[str, bed_reader.open_bed]]= None) -> pd.DataFrame:
        """
        [Perform linear association for each SNP with the phenotype]

        Args:
            bed_file (str): [A bed_reader input, this is a bed file]
            pheno_file_path (str)
            covar_file_path (str)
            phenotype (str, optional): [The phenotype of interest]. Defaults to 'WM_sum'.
            covariate (List[str], optional): [List of phenotypes of interest]. Defaults to ['euro_Anc_PC1', 'euro_Anc_PC2', 'euro_Anc_PC3', 'GA_vol', 'PMA_vol', 'Gender', 'Intracranial_Imperial'].

        Returns:
            pd.DataFrame: [Dataframe, where each row contains result of univariate test for individual SNP]

        Note:
            The ouput can be compared with the plink linear association file.
        """

        if pheno_covar_file is not None:
            if isinstance(pheno_covar_file,str):
                pheno_covar_file = pd.read_table(pheno_covar_file, sep=' ')
        else:
            if pheno_file is None:
                raise Exception("You must provide Phenotype")
            if covar_file is None:
                raise Exception("You must provide Covariates")
            if isinstance(pheno_file,str):
                pheno_file = pd.read_table(pheno_file, sep='\t')
            if isinstance(covar_file,str):
                covar_file = pd.read_table(covar_file, sep='\t')
            pheno_covar_file = pd.merge(pheno_file,
                                        covar_file,
                                        on='FID',
                                        how='left').dropna()
        fid_list = pheno_covar_file.FID.to_list()
        covariate = covar_file.columns.tolist()[2:] # if the first two columns are FID and ID
        #check if new_bed_file is present:
        if not updated_bed_file:
            bed_file = SNPsFunctionalAnalysis.extract_new_bed_file(snps_list=snps_list,
                                            fid_list=fid_list,
                                            bed_file=orig_bed_file)
        else:
            if isinstance(updated_bed_file, str):
                bed_file =  bed_reader.open_bed(updated_bed_file)
            elif isinstance(updated_bed_file, bed_reader.open_bed):
                bed_file = updated_bed_file
            else:
                raise Exception('Your updated bed file is in wrong format')
        if not hasattr(bed_file, 'genotype'): # this is required if i provide the updated bed file
            bed_file.genotype = bed_file.read()
        new_fid_list1 = bed_file.fid.tolist() # to make sure that individuals with different fid values are removed
        new_fid_list2 = [i.split('-')[0] for i in new_fid_list1] #set anything in the fid as no '-' if there is '-' in the fid
        pheno_covar_file = pheno_covar_file[pheno_covar_file['FID'].isin(new_fid_list1+new_fid_list2)]
        try:
            bed_file_chr = bed_file.properties_dict['chromosome']
        except KeyError:
            bed_file_chr = bed_file.properties['chromosome']
        bed_file_A1 = bed_file.properties_dict['allele_1']
        bed_file_SNPs = bed_file.genotype
        bed_file_sid = bed_file.properties_dict['sid']
        bed_file_SNPs = pd.DataFrame(bed_file_SNPs)
        bed_file_SNPs.columns = bed_file_sid
        def perform_univariate_test(X: pd.core.frame.DataFrame, Y: pd.core.frame.DataFrame, dictionary: DefaultDict):
            """[perform univariate test, where the dependent variable is a single column,
            and dependent variable is a dataframe, and the name of the SNP of interest is a column]

            Args:
                X (pd.core.frame.DataFrame): [Independent variable, where the SNP of interest is in a column]
                Y (pd.core.frame.DataFrame): [Dependent variable, single column]
                dictionary (DefaultDict): [Dictionary defined with the keys as the SNP and values stat, P-value, beta]
            """
            X = sm.add_constant(X)
            model = sm.OLS(Y, X, missing='drop')  # drop any missing values
            results = model.fit()
            stat = results.tvalues.iloc[-1]
            p_value = results.pvalues.iloc[-1]
            beta = results.params.iloc[-1]
            dictionary['STAT'] = stat
            dictionary['P'] = p_value
            dictionary['BETA'] = beta
        y = pheno_covar_file[[phenotype]].copy()
        x = pheno_covar_file[covariate].copy()     
        snp_association = defaultdict(dict)
        for snp in tqdm.tqdm(bed_file_sid):
            x['SNP'] = bed_file_SNPs[[snp]].values
            try:
                perform_univariate_test(x, y, snp_association[snp])
            except ValueError:
                print('check your categorical data, make sure it is converted to dummy variables')

        snp_association = pd.DataFrame(snp_association).T
        snp_association['A1'] = bed_file_A1
        snp_association['CHR'] = bed_file_chr
        snp_association.reset_index(inplace=True)
        snp_association.columns = ['SNP'] + snp_association.columns.to_list()[1:]
        snp_association = snp_association[['SNP', 'A1', 'BETA', 'STAT', 'P']]

        return bed_file, snp_association
    
    @staticmethod
    def get_the_best_SNPs(snp_association,
                          pcolumn = 'P', 
                          threshold=0.05)-> pd.DataFrame:
        """Retain only the SNPs that past through a threshold.

        Args:
            snp_association (_type_): dataframe with column names P for p-value and SNP for snps
            threshold (_type_): the p-value threshold. Remove all snps that has association strength less than this.

        Returns:
            DataFrame
        """
        return snp_association[snp_association[pcolumn] <= threshold].reset_index(drop=True)

    @staticmethod
    def SNPs_annotation_to_gene(snps_list: List[str],
                            gene_build_path: str,
                            window_size: int = 0) -> List[pd.DataFrame]:
        """[Annotate SNPs to gene]

        Args:
            snps_list (List[str]): [SNPs list of interest]
            gene_build_path (str): [path to A gene_build downloaded from https://ctg.cncr.nl/software/magma]
            window_size (int, optional): [Symmetric up and down stream window in kilobases from the gene position]. Defaults to 0.

        Returns:
            List[pd.core.frame.DataFrame]: [genes_ID: table of genes and corresponding snps, snp_ID: table of SNPs, and corresponding genes]

        Notes:
            Can be compared with MAGMA annotation file
        """
        genes_ID = defaultdict(dict)
        snp_ID = defaultdict(dict)
        window_size = window_size*1000
        snp_not_found = []
        gene_build = pd.read_table(gene_build_path, header=None, names=['Genes_ID', 'CHR',
                                                                        'Start', 'Stop', 'Strand', 'Gene_Name'])
        for snp in snps_list:
            chromosome = snp.split(':')[0]
            bp = int(snp.split(':')[1])
            try:
                genes = gene_build[(gene_build['CHR'] == chromosome) & (
                    gene_build['Start']-window_size < bp) & (bp < gene_build['Stop']+window_size)].values
            except IndexError:  # the snp not found
                snp_not_found.append(snp)
                continue
            for gene_attr in genes:  # there maybe overlaps
                gene_ID = gene_attr[0]  # 473
                gene_start = gene_attr[2]  # 8412464
                gene_end = gene_attr[3]  # 8877699
                gene_ens_name = gene_attr[5]  # 'RERE'
                if gene_ID not in genes_ID:
                    genes_ID[gene_ID] = defaultdict(list)
                    genes_ID[gene_ID]['CHR'] = chromosome
                    genes_ID[gene_ID]['START'] = gene_start
                    genes_ID[gene_ID]['STOP'] = gene_end
                    genes_ID[gene_ID]['NAME'].append(gene_ens_name)

                genes_ID[gene_ID]['SNP'].append(snp)
                genes_ID[gene_ID]['N_SNP'] = len(genes_ID[gene_ID]['SNP'])

                if snp not in snp_ID:
                    snp_ID[snp] = defaultdict(list)
                snp_ID[snp]['Genes_list'].append(gene_ID)
                snp_ID[snp]['N_Genes'] = len(snp_ID[snp]['Genes_list'])
                snp_ID[snp]['Genes_NAME'].append(gene_ens_name)

        genes_ID = pd.DataFrame(genes_ID).T
        genes_ID = genes_ID.reset_index()
        genes_ID.columns = ['Gene_ID', 'CHR',
                            'START', 'STOP', 'NAME', 'SNP', 'N_SNP']

        snp_ID = pd.DataFrame(snp_ID).T
        snp_ID = snp_ID.reset_index()
        snp_ID.columns = ['SNP_ID', 'Genes_list', 'N_Genes', 'Genes_Name']

        return genes_ID, snp_ID

class GeneSetEnrichment:
    @staticmethod
    def read_gmt(file:str)->list:
        """open and read gmt file (pathway files)
            The pathway entry must have the following format:
            pathway name/url_link/list of genes found in the pathway.
            The entries are tab-separated
        Args:
            file (str): the pathway file of interest

        Returns:
            list: list of list
        """
        genesets = []
        with open(file, 'r') as fin:
            for l in fin:
                genesets.append(l.strip().split("\t"))
        return genesets
    
    @staticmethod
    def read_gene_list(file:str)->list:
        """read gene list. This file must contains only genes in the same corresponding format as in the pathway file. Each gene must be on separate line.

        Args:
            file (str): gene list file

        Returns:
            list: list of genes
        """
        gene_list=[]
        with open(file,'r') as fin:
            for l in fin:
                gene_list.append(l.strip())
        return gene_list
    
    @staticmethod
    def hypergeometric_test(pathways:list,
                            background_genes:np.array,
                            genes:np.array):
        """
        hypergeometric test as done in FUMA-webapp.
        original source code: https://github.com/vufuma/FUMA-webapp/blob/master/scripts/GeneSet.py
        See ypTest and GeneSetTest function in that FUMA link.
        """
        
        def intersection(a1:np.array,a2:np.array)->np.array:
            """Return indices of values in a1 that are found in a2
            """
            return np.where(np.in1d(a1, a2))[0]
        
        g = np.asarray(pathways[2:])
        g = g[intersection(g,background_genes)]
        n = len(g)
        gin = genes[intersection(genes,g)]
        x = len(gin)
        if x>1:
            p = hypergeom.sf(x-1,len(background_genes),n,len(genes))
        else:
            p = 1
        return n,x,p,":".join(gin.astype(str))
    
    @staticmethod
    def ora(pathways:Union[str,list],
            background_genes:Union[str,list,np.array],
            genes:Union[str,list,np.array],
            multiple_comparison:str='bonferroni',**kwargs)->pd.DataFrame:
        """Perform overrepresentation analysis

        Args:
            pathways (Union[str,list]): file name or list of list of pathways
            background_genes (Union[str,list,np.array]): file name or list of background genes
            genes (Union[str,list,np.array]): filename or list of genes of interest
            multiple_comparison (str, optional): the multiple comparison method. Defaults to 'bonferroni'. bonferroni = 0.05/len(pathways)

        Returns:
            pd.DataFrame
        """
        if isinstance(background_genes,str):
            background_genes = GeneSetEnrichment.read_gene_list(background_genes)
        if not isinstance(background_genes,np.ndarray):
            background_genes = np.array(background_genes)
        if isinstance(genes,str):
            genes = GeneSetEnrichment.read_gene_list(genes)
        if isinstance(genes,list):
            if not all(isinstance(i,str) for i in genes):
                genes = [str(i) for i in genes]
        if not isinstance(genes,np.ndarray):
            genes = np.array(genes)
        if isinstance(pathways,str):
            pathways = GeneSetEnrichment.read_gmt(pathways)
        
        output = pd.DataFrame([])

        disable_tqdm = kwargs.get('disable_tqdm',False)
        for l in tqdm.tqdm(pathways,disable=disable_tqdm):
            if len(l)<3:
                continue
            n,x,p,g_overlapped = GeneSetEnrichment.hypergeometric_test(l,background_genes,genes)
            temp = pd.DataFrame({'GeneSet':[l[0]],
                                    'N_genes':[n],
                                    'N_overlap':[x],
                                    'p':[p],
                                    'genes':[g_overlapped]})
            output = pd.concat([output,temp],axis=0)
        output = output.reset_index(drop=True)
        if multiple_comparison == 'bonferroni':
            output['adjP'] = output['p'].apply(lambda x: 1 if x*len(pathways)>1 else x*len(pathways))
        elif multiple_comparison == 'fdr':
            survived,adjusted_pval = fdrcorrection(output['p'],alpha=0.05)
            output['adjP'] = adjusted_pval
        return output
        