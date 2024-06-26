"""
visualisation.py
This is a visualisation file, containing all the necessary visualisations.
You can draw simple plots, Bar or Scatter, or the Brain segmentation
"""
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from . import stats
import seaborn as sns
from scipy.stats import ttest_ind
import statsmodels.api as sm
from typing import List, Union, Optional
import nibabel as nib # used to do visualise brain maps
import copy
from matplotlib.collections import LineCollection
import matplotlib.patches as mpatches
import matplotlib as mpl
from matplotlib.colors import ListedColormap, to_rgb, rgb2hex, CSS4_COLORS
from decimal import Decimal

from collections import defaultdict
from itertools import product, chain

from functools import reduce  # forward compatibility for Python 3
import operator

class SimplePlots:
    
    @staticmethod
    def return_array(x=None,
                 data=None,
                 must_be=None,
                 return_array=True,
                 variable_label=None) -> np.ndarray:
        """
        Convenience function to take in multiple data types and return numpy array

        Parameters
        ----------
        x : Union[np.ndarray,pd.DataFrame,pd.Series,str,List[Union[str,float,
            int,pd.Series,np.ndarray]]], optional
            The variable of interest. The default is None.
        data : Optional[pd.DataFrame], optional
            The pd.DataFrame if providing column names as x. The default is None.
        must_be : Optional[str], optional
            {str,int,float}. np.ndarray.astype() will be applied The default is None.
        variable_label : Optional[str], optional
            DESCRIPTION. The default is None.

        Raises
        ------
        TypeError
            DESCRIPTION.

        Returns
        -------
        x : np.ndarray
            The returned array.
        variable_label
            the name of the variable x.
        column_names
            the column of each column in x if x is multi-dimensional.

        """
        if x is None:
            return x,None,None
        
        else:
            if isinstance(x,(pd.DataFrame,pd.Series)):
                x = pd.DataFrame(x) if isinstance(x,pd.Series) else x
                variable_label = x.columns.tolist() if variable_label is None else variable_label
                x = x.values
            if isinstance(x,str):
                x = [x]
            if isinstance(x,np.ndarray):
                if x.ndim == 1:
                    x = [x]
            if isinstance(x,list):
                if all(isinstance(i,str) for i in x):
                    assert isinstance(data,pd.DataFrame), 'missing the dataframe'
                    variable_label = x if variable_label is None else variable_label
                    x = data[x].values 
                elif all(isinstance(i,list) for i in x): # list of list
                    x = np.array(x).T
                elif all(isinstance(i,pd.Series) for i in x): # list of series
                    variable_label = [i.name for i in x]
                    x = np.array(x).T
                elif all(isinstance(i,np.ndarray) for i in x):
                    x = np.array(x).T
                    if x.ndim > 2:
                        raise TypeError('if providing list of arrays, arrays must be 1 dimensional')
                elif all(isinstance(i,(float,int)) for i in x):
                    x = np.array(x).reshape(-1,1)
            
            if variable_label is None:
                variable_label = ['None' for i in range(x.shape[1])]
            variable_label = [variable_label] if isinstance(variable_label,str) else variable_label
            if len(variable_label) != x.shape[1]:
                    variable_label = [variable_label[0] for i in range(x.shape[1])]

            if must_be is not None:
                x = x.astype(must_be)
            if not return_array:
                x = list(chain.from_iterable(x))
            return x,variable_label,variable_label
            
    class Groupby:
        
        @staticmethod
        def groupby(*args,**kwargs)->dict:
            """
            Perform groupby operation based on several arguments to return a defaultdict dictionary
            It is recommended for the args to be discrete or categorical variables (because we are taking the unique values)
            Kwargs can be both categorical or continuous. But if it is for a bar plot, it should be continuous variables.
            This function is similar to using pd.DataFrame groupby, pd.set_index.
            You can have as many level of args or kwargs as you want.
            Usage example:
                x = ['foo1', 'foo2', 'foo1', 'foo2']
                y = [-0.4, 0.3, 1.4, 1.3] 
                color = ['red', 'blue', 'red', 'red'] 
                gender = [2, 1, 1, 3]
            groupby(x,y=y): will group by x values. to produce
            {'foo1':{'y':[-0.4,1.4]},'foo2':{'y':[0.3,1.3]}}
            groupby(x,color,y=y) will group by x and color value to produce
            {'foo1': {'blue': defaultdict(list, {'y': []}),
              'red': defaultdict(list, {'y': [-0.4, 1.4]})},
             'foo2': {'blue': defaultdict(list, {'y': [0.3]}),
              'red': defaultdict(list, {'y': [1.3]})}}
            grouby(x,color,y=y,gender=gender) will groupby by x and color value to produce
            {'foo1': {'blue': defaultdict(list, {'y': [], 'gender': []}),
              'red': defaultdict(list, {'y': [-0.4, 1.4], 'gender': [2, 1]})},
             'foo2': {'blue': defaultdict(list, {'y': [0.3], 'gender': [1]}),
              'red': defaultdict(list, {'y': [1.3], 'gender': [3]})}})
            
            
            Parameters
            ----------
            *args : np.ndarray
                set of discrete or categorical variables
            **kwargs : np.ndarray
                the values to plot (e.g. on y-axis or to color the bar by)

            Returns
            -------
            temp_plot_dict : dict
                A nested dictionary, where the dictionary keys are made up of the *args,
                and the values in the deepest layer are the **kwargs

            """
            # create a dictionary set that contains as keys all the possible combinations of arguments
            def dictionary_merge(dict1,dict2):
            #convenience function to merge nested dictionary together
                for key in dict2:
                    if key in dict1:
                        if isinstance(dict1[key],dict) and isinstance(dict2[key],dict):
                            dictionary_merge(dict1[key],dict2[key])
                    else:
                        dict1[key]=dict2[key]
                return dict1
            
            temp_plot_dict=defaultdict(dict)
            args = [i for i in args if i is not None]
            kwargs = {k:v for k,v in kwargs.items() if v is not None}
            all_unique_keys = [tuple(set(i)) if not isinstance(i,np.ndarray) else tuple(set(i.flatten())) for i in args]
            all_possible_keys = product(*all_unique_keys)
            all_values = list(kwargs.keys())
            for keys_combo in all_possible_keys:
                temp_dict = defaultdict(list)
                for value in all_values:
                    temp_dict[value] = []
                for i in reversed(keys_combo):
                    temp_dict = {i:temp_dict}
                for key,value in temp_dict.items():
                    if key in temp_plot_dict:
                        temp_plot_dict[key] = dictionary_merge(temp_plot_dict[key],value)
                    else:
                        temp_plot_dict[key] = value
            len_args = len(args)
            for key_vals in zip(*args,*kwargs.values()):
                keys = key_vals[:len_args]
                keys = tuple(k if not isinstance(k,np.ndarray) else k[0] for k in keys)
                vals = key_vals[len_args:]
                vals = tuple(v if not isinstance(v,np.ndarray) else v[0] for v in vals)
                obj = temp_plot_dict[keys[0]]
                for key_idx,key in enumerate(keys):
                    if key_idx != 0:
                        obj = obj[key] if not isinstance(key,np.ndarray) else obj[key[0]]
                    for idx,name_val in enumerate(all_values):
                        if name_val in obj:
                            obj[name_val].append(vals[idx])
            
            return temp_plot_dict

        @staticmethod
        def groupby_operation(groupby_dict:dict,operation:Union[dict,str])->dict:
            """
            Perform groupby operation on the output of groupby function.
            Performs recursive opening of the nested dictionary to perform some
            operations on the last layer of the dictionary
            
            NOTE:This is necessary in case you didn't provide a dataframe with unique values
            
            Parameters
            ----------
            groupby_dict : dict
                Nested dictionary, output from groupby function

            operation : Union[dict,str]
                operation to be performed on the deepest layer of the nested dictionary
                IF str:{'sum','mean','count','first','last','max','min'}.
                This operation will be applied to all lists in the last layer irrespective of the name.
                IF dict, the key must be the key of the lists in the last layer.
                e.g. {'y':'sum','color':'first'}. This will find the key y
                in the last layer and perform sum but will find the key color and perform first.
                
            Returns
            -------
            dict
                Updated groupby_dict
            """
            def do_operation(v,operation):
                if len(v) == 0:
                    v = [0]
                if all(isinstance(item,str) for item in v):
                    operation = 'first' if operation is None else operation
                    if operation =='first':
                        return v[0]
                    elif operation =='last':
                        return v[-1]
                elif all(isinstance(item,(float,int)) for item in v):
                    operation = 'sum' if operation is None else operation
                    if operation == 'sum':
                        return np.sum(v)
                    elif operation == 'mean':
                        return np.mean(v)
                    elif operation == 'count':
                        return np.count_nonzero(v)
                    elif operation == 'max':
                        return np.max(v)
                    elif operation == 'min':
                        return np.min(v)
    
            def find_last_depth(obj,operation):
                #convenience function to recursively perform some function on
                # the deepest layer of a nested function
                for k,v in obj.items():
                    if isinstance(v,dict):
                        find_last_depth(v,operation)
                    else:
                        if isinstance(operation,dict):
                            assert k in operation, 'f{k} not in available groupby operations'
                            obj[k] = do_operation(v,operation[k])
                        else:
                            obj[k] = do_operation(v,operation)
                return obj
            
            return find_last_depth(groupby_dict,operation) 
    
    @staticmethod
    def sort_array(current_array,order=None,ascending=True,specific_order=None):
        if specific_order is None:
            new_array = np.sort(current_array,order=order)
            if not ascending:
                new_array = new_array[::-1]
        else:
            new_array = pd.DataFrame(current_array)
            for key,values in specific_order.items():
                new_array[key] = pd.Categorical(new_array[key],categories=values,ordered=True)
            new_array = new_array.sort_values(by=['separateby','x','hue'])
            new_array = new_array.to_records(index=False)
        return new_array
    
    @staticmethod
    def get_color_pallete(colorby:np.ndarray=None,cmap:str=None,cmap_reversed:bool=False):
        #convenience function to get color pallete and scalar mapable
        # color will be consistent across multiple plots if seperateby is defined.
        if colorby is None:
            return None,None
        pal = sns.color_palette(cmap,len(colorby))
        if cmap_reversed:
            pal = pal[::-1]
        rank = colorby.argsort().argsort()
        my_cmap = ListedColormap(pal)
        norm = plt.Normalize(colorby.min(),colorby.max())
        scalar_mappable = plt.cm.ScalarMappable(cmap=my_cmap,norm=norm)
        scalar_mappable.set_array([])
        color = np.array(pal)[rank]
        return color,scalar_mappable
    
    @staticmethod
    def plot_legend_loc(ax,return_stats=True,plot_legend=True,**figkwargs):
        if return_stats:
            if plot_legend:                
                if figkwargs['legend_loc']=='outside':
                    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
                else:
                    ax.legend(loc=figkwargs['legend_loc'])
        

    @staticmethod
    def Bar(x: Union[np.ndarray,pd.DataFrame,pd.Series,list,str],
            y: Union[np.ndarray, pd.DataFrame, pd.Series,list, str],
            annotate: Union[np.ndarray,pd.DataFrame,pd.Series,list,str]=None,
            colorby:Union[np.ndarray,pd.DataFrame,pd.Series,list,str]=None,
            separateby:Union[np.ndarray,pd.DataFrame,pd.Series,list,str]=None,
            hue: Union[np.ndarray,pd.DataFrame,pd.Series,list,str] = None,
            order:Optional[Union[list,dict,str]]='y',
            data: Optional[pd.DataFrame] = None,
            groupby_operation:Union[str,dict]=None,
            title:Optional[str] = None,
            orientation:Optional[str]='vertical',
            fig:Optional[plt.Figure] = None,
            ax:Optional[plt.Axes] = None, **figkwargs) -> Optional[plt.Axes]:
        """
        Create bar plot.
        
        Parameters
        ----------
        x : Union[np.ndarray,pd.DataFrame,pd.Series,list,str]
            X-axis. Must be categorical data
        y : Union[np.ndarray, pd.DataFrame, pd.Series,list, str]
            Y-axis. Must be continuous data
        annotate : Union[np.ndarrxeft side. Must be continuous data. used to draw point plots
        colorby : Union[np.ndarray,pd.DataFrame,pd.Series,list,str], optional
            Continuous data that can be used to color each bar. The default is 
            None.
        separateby : Union[np.ndarray,pd.DataFrame,pd.Series,list,str], optional
            Categorical data that can be used to separate different plots. The 
            default is None.
        hue : Union[np.ndarray,pd.DataFrame,pd.Series,list,str], optional
            Categorical data that can be used to separate different bars in the
            same plot. The default is None.
            If both colorby and hue is defined, then colorby will be ignored.
        order: Union[list,dict,str]:
            Define the order of the bars.
            Default is 'y': This will oder the bar in the ascending order of y
            other option include ['seperateby','x','hue','y','colorby'] where 
            separateby, x and hue can be ordered alphabetically, and y, colorby
            ordered numerically. Set order_reversed to True or False to ascending
            or descending.
            if specific order is required. Provide a dictionary
            e.g. {'x':['a','b','c','d']} and the bars will order by the list.
        data : Optional[pd.DataFrame], optional
            DataFrame from which to get the values from . The default is None.
        groupby_operation : Union[str,dict], optional
            perform function to 'y' and 'colorby'
            Possible operations include
            {sum,mean,max,min,first,last}
            if same groupby operation on y and colorby, use string.
            if different groupby operations on y and colorby, use dictionary to
            define .E.g. {'y':'sum','colorby':'max'} will perform sum on 'y' 
            values but color each bar by the max colorby value. The default is 
            'sum'.
        title : str, optional
            Title of the whole plot. The default is None.
        xlabel : str, optional
            Label on the x-axis. The default is None.
        ylabel : str, optional
            Label on the y-axis. The default is None.
        fig: Optional[plt.Figure],optional
            Can use fig defined by the user. Needed if providing ax and requires
            colorbar
        ax : Optional[plt.Axes], optional
            Can use ax defined by the user. The default is None.
        **figkwargs : dict
            yscalelog:bool: if True, y-axis becomes log10scale, default False
            alpha: float: set the transparency of the bars. Default 0.5
            hline:float: if float defined, then plot a hline line on 
                                y-axis.
            hline_label: label of hline
            rotation_x:int,float: degree of rotation on the x-ticks
            colorbar_axes:List[float]: if multiple subplots, then define the 
            colorbar position. The list define the co-ordinate of the lower left
                corner of the color bar. The last two values defines the width 
                and height of the bar. default is [0.85, 0.15, 0.01, 0.7]
            colorbar_label:str: label on the colorbar.
            cmap:str to color the bars if used colorby. See sns cmap for options. 
                Default is 'Greens'
            cmap_reversed: to reverse the cmap. Default False
            xlabel_pos: tuple(float): If multiple subplots, the define position
            of the x-label. Default (.48,.01)
            ylabel_pos:tuple(float): If multiple subplots, the define position
            of the x-label. Default (.1,.5)
            figsize:tuple(float or int): define fig size.
            barwidth:float: Define bar width. Default 0.35.

        Raises
        ------
        AttributeError
            colorbar_label requires colorby.

        Returns
        -------
        fig
           return fig ploted 

        """
        x,xlabel,_ = SimplePlots.return_array(x,data=data,must_be='str',return_array=False)
        y,ylabel,_ = SimplePlots.return_array(y,data=data,return_array=False)
        annotate,_,_ = SimplePlots.return_array(annotate,data=data,must_be='str',return_array=False)
        colorby,colorbar_label,_ = SimplePlots.return_array(colorby,data=data,return_array=False)
        separateby,plot_label,_ = SimplePlots.return_array(separateby,data=data,must_be='str',return_array=False)
        hue,legend_label,_ = SimplePlots.return_array(hue,data = data,must_be='str',return_array=False)
        if (hue is not None) and (colorby is not None):
            #if both hue and colorby is present, show only hue
            colorby = None
            colorbar_label = None
        if separateby is None:
            separateby = [None for i in range(len(x))]
        if colorby is None:
            colorby = [0 for i in range(len(x))]
        if hue is None:
            hue = [None for i in range(len(x))]
        if annotate is None:
            annotate = [None for i in range(len(x))]
        #you want to groupby x in case x is not unique.
        to_plot_dictionary = SimplePlots.Groupby.groupby(separateby,x,hue,y=y,colorby=colorby,annotate=annotate)
        
        to_plot_dictionary = SimplePlots.Groupby.groupby_operation(to_plot_dictionary,
                                                                    operation=groupby_operation)
        
        all_bars = list(set(product(separateby,x,hue))) # all the bars combinations
        
        def getFromDict(dictionary,mapList):
            #convenience function where you get the values from dictionary by passing a list of keys.
            return reduce(operator.getitem, mapList,dictionary)
        def get_unique(x:np.ndarray):
            #conveninece function to return unique values but in preserved order
            if isinstance(x,list):
                new_x = np.ndarray(x)
            else:
                new_x = x.copy()
            _,idx = np.unique(new_x,return_index=True)
            return new_x[np.sort(idx)]
        
        all_values = []
        for keys in all_bars: # [dict][key1][key2][key3]
            all_values.append(tuple(getFromDict(to_plot_dictionary,keys).values()))
        all_bars_vals = np.array([bar+val for bar,val in zip(all_bars,all_values)],
                                 dtype=[('separateby','O'),
                                        ('x','O'),
                                        ('hue','O'),
                                        ('y',float),
                                        ('colorby',float),
                                        ('annotate','O')])
        
        if order is not None:
            
            if 'order_reversed' not in figkwargs:
                figkwargs['order_reversed'] = False
            if isinstance(order,dict):
                for k,v in order.items():
                    assert len(set(all_bars_vals[k])) == len(v), f'the number of values in {k} in order argument does not match the provided dataframe'
                    assert set(v).issubset(all_bars_vals[k]), f'you have provided wrong names in {k} in order argument'
                all_bars_vals = SimplePlots.sort_array(all_bars_vals,
                                                        specific_order=order)
            else:
                try:
                    all_bars_vals = SimplePlots.sort_array(all_bars_vals,
                                                        order=order,
                                                        ascending=figkwargs['order_reversed'])
                except TypeError:
                #this happens when the continuous values has equal values, e.g, 0.000 in multiple places, the code will then try to sort the rows by the first axis. If that first axis is None, then it will throw bad error.
                    try:
                        assert all(v is None for v in all_bars_vals['separateby']) #make sure that all of the values in all_bar_vals separateby is None.
                    except AssertionError:
                        raise TypeError('The separateby value is not None, there is something wrong with sorting process')
                    all_bars_vals['separateby'] = 0
                    all_bars_vals = SimplePlots.sort_array(all_bars_vals,
                                                        order=order,
                                                        ascending=figkwargs['order_reversed'])
                    all_bars_vals['separateby'] = None
                    
        separateby = all_bars_vals['separateby']
        if all(item is None for item in separateby):
            separateby = None
        x = all_bars_vals['x']
        hue = all_bars_vals['hue']
        if all(item is None for item in hue):
            hue = None
        y = all_bars_vals['y']
        colorby = all_bars_vals['colorby']
        annotate= all_bars_vals['annotate']
        if all(item==0 for item in colorby):
            colorby = None
        if all(item is None for item in annotate):
            annotate = None
        
        #Here you have two np.arrays: all_bars = nx3 shape where 
        #column1=separateby column2=x column3= hue
        #all_values = nx2 column1 = y, column2 = colorby
        
        # for visualisation you can plot the bar plot separated by 3 values.
        # between unique x, separateby and hue values.
        # you can plot on the y axis and color the bars
        
        x_pos = len(np.unique(x))
        x_pos = np.arange(1,x_pos+1) # position on the x axis.
        
        if 'xlabel' not in figkwargs:
            figkwargs['xlabel'] = xlabel
        if 'ylabel' not in figkwargs:
            figkwargs['ylabel'] = ylabel
        if 'yscalelog' not in figkwargs:
            figkwargs['yscalelog'] = False
        if 'alpha' not in figkwargs:
            figkwargs['alpha'] = 1
        if 'hline' not in figkwargs:
            figkwargs['hline'] = None
        if 'hline_label' not in figkwargs: 
            figkwargs['hline_label'] = None
        if 'rotation_x' not in figkwargs:
            figkwargs['rotation_x'] = 0
        if 'colorbar_axes' not in figkwargs:
            figkwargs['colorbar_axes'] = [0.95, 0.15, 0.01, 0.7]
        if 'colorbar_label' not in figkwargs:
            figkwargs['colorbar_label'] = colorbar_label
        if 'cmap' not in figkwargs:
            figkwargs['cmap'] = 'coolwarm'
        if 'cmap_reversed' not in figkwargs:
            figkwargs['cmap_reversed'] = False
        if 'legend_label' not in figkwargs:
            figkwargs['legend_label'] = legend_label
        if 'legend_loc' not in figkwargs:
            figkwargs['legend_loc'] = 'outside'
        if 'plot_label' not in figkwargs:
            figkwargs['plot_label'] = plot_label
        if 'plot_title_fontsize' not in figkwargs:
            figkwargs['plot_title_fontsize'] = 10
        if 'xlabel_pos' not in figkwargs:
            figkwargs['xlabel_pos'] = (.48,.01)
        if 'ylabel_pos' not in figkwargs:
            figkwargs['ylabel_pos'] = (.1,.5)
        if 'figsize' not in figkwargs:
            figkwargs['figsize'] = None
        if 'barwidth' not in figkwargs:
            figkwargs['barwidth'] = 0.35
        if 'annotate_fontsize' not in figkwargs:
            figkwargs['annotate_fontsize'] = 10

        if separateby is not None: # plot different category into different plots. Useful when you want to show a common colorbar
            uniq_separateby = get_unique(separateby)
            if ax is None:
                if len(uniq_separateby)>3:
                    row = int(np.ceil(len(uniq_separateby)/3))
                    column = 3
                else:
                    row =1
                    column = len(uniq_separateby)
                fig,axes = plt.subplots(row,column,sharex=True,sharey=True,figsize=figkwargs['figsize'])
                if isinstance(axes,plt.Axes):
                    axes = [axes]
                else:
                    if len(axes) > 1:
                        axes = axes.flatten()
                    else:
                        axes = [axes]
            else:
                if isinstance(ax,plt.Axes):
                    axes=[ax]
                    row,column = 1,1
                else:
                    assert all(isinstance(i,plt.Axes) for i in ax), 'you have not provided axes'
                    axes = ax
                    row = axes[0].get_gridspec().nrows
                    column = axes[0].get_gridspec().ncols
        else:
            row,column = 1,1
            if ax is None:
                fig, ax = plt.subplots(figsize=figkwargs['figsize'])
            axes = [ax]

        if colorby is not None: # color of the bar, it will be consistent across multiple plots if seperateby is defined.
            pal = sns.color_palette(figkwargs['cmap'],len(colorby))
            if figkwargs['cmap_reversed']:
                pal = pal[::-1]
            rank = colorby.argsort().argsort()
            my_cmap = ListedColormap(pal)
            norm = plt.Normalize(colorby.min(),colorby.max())
            sm = plt.cm.ScalarMappable(cmap=my_cmap,norm=norm)
            sm.set_array([])
            color = np.array(pal)[rank]
        else:
            color = None
            
        if figkwargs['yscalelog']:
            bottom = min(y)
            if bottom < 1:
                bottom = bottom/10
            else:
                bottom = bottom*10
            plt.yscale('log')
        else:
            bottom = 0
        
        if hue is not None:
            def plot_group_bar_chart(x_pos,
                                     y,
                                     barwidth,
                                     label_idx,
                                     label,
                                     unique_hue,
                                     ax,
                                     annotate=None,
                                     color=None,
                                     alpha=None,
                                     log=False,
                                     bottom=0,
                                     orientation='vertical'):
                mean_pos = np.arange(1,len(unique_hue)+1).mean()
                if len(unique_hue)%2==0:
                    shift = (label_idx+1) - int(np.ceil(mean_pos))
                else:
                    shift = (label_idx+1) - int(np.floor(mean_pos))
                pos = x_pos+(shift*barwidth/len(unique_hue))
                if orientation == 'horizontal':
                    ax.barh(pos,
                            y,
                            barwidth/len(unique_hue),
                            color=color,label=label,alpha=alpha,log=log)
                    if annotate is not None:
                        for to_annotate,height,position in zip(annotate,y,pos):
                            ax.annotate(to_annotate,xy=(height,position),ha='left',va='center',fontsize=figkwargs['annotate_fontsize'])
                else:
                    ax.bar(pos,
                           y,
                           barwidth/len(unique_hue),
                           color=color,label=label,alpha=alpha,log=log,bottom=bottom)
                    if annotate is not None:
                        for to_annotate,height,position in zip(annotate,y,pos):
                            ax.annotate(to_annotate,xy=(position,height),ha='center',va='bottom',fontsize=figkwargs['annotate_fontsize'])
                return ax

        for idx, ax in enumerate(axes):
            if separateby is not None:
                try:
                    current_separateby_index = np.where(separateby==uniq_separateby[idx])
                except IndexError:
                    #this is because you have empty subplots
                    continue
                temp_x = x[current_separateby_index]
                # sort_indices_in_x = temp_x.argsort()
                # temp_x = temp_x[sort_indices_in_x]
                temp_y = y[current_separateby_index]
                # temp_y = temp_y[sort_indices_in_x]
                temp_x_pos = np.arange(len(np.unique(temp_x)))
                temp_hue = hue[current_separateby_index] if hue is not None else None
                color_separately = color[current_separateby_index] if color is not None else None
                temp_annotate = annotate[current_separateby_index] if annotate is not None else None
                
                if hue is not None:
                    unique_hue = get_unique(hue)
                    for label_idx,label in enumerate(unique_hue):
                        temp_to_annotate = None if temp_annotate is None else temp_annotate[np.where(temp_hue == label)] # this is necessary because if temp_annotate is NoneType, you can't do indexing.
                        ax = plot_group_bar_chart(
                            temp_x_pos,
                            temp_y[np.where(temp_hue == label)],
                            figkwargs['barwidth'],
                            label_idx,
                            label,
                            unique_hue,
                            ax,
                            annotate=temp_to_annotate,
                            color=color_separately,
                            alpha=figkwargs['alpha'],
                            log=figkwargs['yscalelog'],
                            bottom=bottom,
                            orientation=orientation)
                        if annotate is not None:#plot point plot on the second plot not yet implemented
                            pass
                else:
                    if orientation == 'horizontal':
                        ax.barh(temp_x_pos,temp_y,color=color_separately,
                                alpha=figkwargs['alpha'],
                                log=figkwargs['yscalelog'])
                        if temp_annotate is not None:
                            for to_annotate,height,position in zip(temp_annotate,temp_y,temp_x_pos):
                                ax.annotate(to_annotate,xy=(height,position),ha='left',va='center',fontsize=figkwargs['annotate_fontsize'])
                    else:
                        ax.bar(temp_x_pos,temp_y,color=color_separately,
                               alpha=figkwargs['alpha'],
                               log=figkwargs['yscalelog'],bottom=bottom)
                        if temp_annotate is not None:
                            for to_annotate,height,position in zip(temp_annotate,temp_y,temp_x_pos):
                                ax.annotate(to_annotate,xy=(position,height),ha='center',va='bottom',fontsize=figkwargs['annotate_fontsize'])
                            
                if figkwargs['plot_label'] is None:
                    figkwargs['plot_label'] = ''
                ax.set_title(f"{figkwargs['plot_label']}|{uniq_separateby[idx]}",fontsize=figkwargs['plot_title_fontsize'])
                if orientation == 'horizontal':
                    ax.set_yticks(temp_x_pos,get_unique(temp_x))
                else:
                    ax.set_xticks(temp_x_pos,get_unique(temp_x))
                ax.set(xlabel=None)
                ax.set(ylabel=None)
            
            else:
                if hue is not None:
                    unique_hue = get_unique(hue)
                    for label_idx,label in enumerate(unique_hue):
                        temp_to_annotate = None if annotate is None else annotate[np.where(hue==label)]
                        ax = plot_group_bar_chart(x_pos, 
                                             y[np.where(hue == label)],
                                             figkwargs['barwidth'], 
                                             label_idx, 
                                             label, 
                                             unique_hue,
                                             ax,
                                             annotate=temp_to_annotate,
                                             color=None,
                                             alpha=figkwargs['alpha'],
                                             log=figkwargs['yscalelog'],
                                             bottom=bottom,
                                             orientation=orientation)
                else:
                    if orientation == 'horizontal':
                        ax.barh(x_pos,y,color=color,alpha=figkwargs['alpha'],
                               log=figkwargs['yscalelog'])
                        if annotate is not None:
                            for to_annotate,height,position in zip(annotate,y,x_pos): 
                                ax.annotate(to_annotate,xy=(height,position),ha='left',va='center',fontsize=figkwargs['annotate_fontsize'])
                        
                    else:
                        ax.bar(x_pos,y,color=color,alpha=figkwargs['alpha'],
                               log=figkwargs['yscalelog'],bottom=bottom)
                        if annotate is not None:
                            for to_annotate,height,position in zip(annotate,y,x_pos):
                                ax.annotate(to_annotate,xy=(position,height),ha='center',va='bottom',fontsize=figkwargs['annotate_fontsize'])
                    
                if orientation == 'horizontal':
                    ax.set_yticks(x_pos,get_unique(x))
                else:
                    ax.set_xticks(x_pos,get_unique(x))
            
            if figkwargs['hline'] is not None:
                number_of_plots = 1 if separateby is None else len(uniq_separateby)
                neg_if_more_than_one = 1 if number_of_plots == 1 else -1 ### wonders of matplotlib
                if not isinstance(figkwargs['hline'],list):
                    figkwargs['hline'] = [figkwargs['hline']]
                if figkwargs['hline'] is not None:
                    if not isinstance(figkwargs['hline_label'],list):
                        figkwargs['hline_label'] = [figkwargs['hline_label']]
                else:
                    if len(figkwargs['hline']) > 1:
                        raise TypeError('must provide a list of labels for different hlines')
                    else:
                        figkwargs['hline_label'] = []
                for hline,hline_label,hline_colour in zip(figkwargs['hline'],figkwargs['hline_label'],list('bgrcmykw')):        
                    ax.hlines(hline,
                            x_pos[0]-number_of_plots*figkwargs['barwidth'],
                            x_pos[-1]+neg_if_more_than_one*figkwargs['barwidth'],
                            label=hline_label,
                            color=hline_colour)
            if 'xlabel_fontdict' not in figkwargs:
                figkwargs['xlabel_fontdict'] = 10
            
            if row > 1:
                if (idx >= 3):
                    ax.tick_params(axis='x',
                                   rotation=figkwargs['rotation_x'],
                                   labelsize=figkwargs['xlabel_fontdict'])

            else:
                ax.tick_params(axis='x',
                               rotation=figkwargs['rotation_x'],
                               labelsize=figkwargs['xlabel_fontdict'])
                
            # if figkwargs['yscalelog']:
            #     ax.set_yscale('log')
        
        if hue is not None or figkwargs['hline_label'] is not None:
            if row > 1:
                ax = axes[2]
            else:
                ax = axes[-1]
            if figkwargs['legend_loc'] == 'outside' or figkwargs['legend_loc'] == 'center left':
                ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
            else:
                ax.legend(loc=figkwargs['legend_loc'])
        
        if figkwargs['colorbar_label'] is not None:
            if colorby is None:
                raise AttributeError('you have not defined colorby and you want to have a color label')
            cbar_ax = fig.add_axes(figkwargs['colorbar_axes'])
            cbar = ax.figure.colorbar(sm, cax=cbar_ax)
            cbar.set_label(figkwargs['colorbar_label'], size=12)

        if len(axes) > 1:
            fig.subplots_adjust(right=0.80)
            fig.text(figkwargs['xlabel_pos'][0], 
                     figkwargs['xlabel_pos'][1], 
                     figkwargs['xlabel'], 
                     ha='center', size='xx-large')
            fig.text(figkwargs['ylabel_pos'][0], figkwargs['ylabel_pos'][1],
                     figkwargs['ylabel'],
                     va='center',
                     rotation='vertical',
                     size='xx-large')
            fig.suptitle(
                title,
                size='xx-large')
        
        else:
            ax.set_xlabel(figkwargs['xlabel'])
            ax.set_ylabel(figkwargs['ylabel'])

    @staticmethod
    def Scatter(x: Union[np.ndarray, pd.DataFrame, pd.Series, str,list],
                y: Union[np.ndarray, pd.DataFrame, pd.Series, str,list],
                colorby:Union[np.ndarray,pd.DataFrame,pd.Series,list,str]=None,
                hue:str = None,
                data: Optional[pd.DataFrame] = None,
                annotate:Optional[str] = None,
                combined: Optional[bool] = False,
                title: Optional[str] = None,
                fig:Optional[plt.Figure] = None,
                ax:Optional[plt.Axes] = None,
                return_stats:bool=True,
                adjust_covar:Optional[dict]=None,
                plot_type:str='grid',
                scaling:Optional[str] = 'both', **figkwargs) -> None:
        """
        Fit linear regression, where y~x. calculates the pval and beta coefficient.
        
        You can use it to visualise across different populations and generate separate pval and beta coeficient for each population (hue) or for all of them combined
        Note: when you have two variables, the pearson's correlation coefficient is the same as the standardized beta coefs.
        Parameters
        ----------
        x : Union[np.ndarray, pd.DataFrame, pd.Series, str]
            value on x.
        y : Union[np.ndarray, pd.DataFrame, pd.Series, str]
            value on y.
            if providing a list of strings (i.e., columns names)
            then plot by hue is implied. Make sure that x is in 2 dimension.
        colorby:Union[np.ndarray, pd.DataFrame, pd.Series, str]
            value to color the scatter points.
        hue:str
            separate data point by another value in the dataframe (e.g. cohort).
            It will calculate separate beta and p-value.
            The default is None. Must provide data frame
            NOTE: defining hue is the same as defining multiple columns. For example, you want to plot different 
        data : Optional[pd.DataFrame], optional
            if providing string x,y, then data will be the dataframe. The default is None.
        combined : Optional[bool], optional
            If use, calculate the total (for all hues) p-val and beta coefs. The default is False.
        title : str, optional
            Title of the graph. The default is None.
        fig : plt.Figure, optional
            The matplotlib figure. The default is None 
        ax : plt.Axes, optional
            The matplitlib axes. The default is None.
        return_stats: bool, optional
            Whether to calculate the statistics. The default is False.
        adjust_covar: dict, optional
            provide variable names to adjust the x or y axes.
            E.g, {'x':['sex','age'], 'y':['age^2']}
            Here, the values in x and y axes will be fitted to a linear regrssion model
            with the name values in the list used as covariates.
        scaling : str, optional
            whether to scale x and y. The default is 'both'.
        plot_multi_plot=True
        **figkwargs :
            xlabel: str
            ylabel: str
            color_label: str
            colorbar_axes: list. Default [0.95, 0.15,0.01,0.7]
            cmap: str. Defaults 'Blues'
            cmap_reversed: bool .Defaults False
            edgecolors: Defaults face.
            linewdith: float
            markersize: float
            legend: bool.
            legend_loc: str
            fontsize: float
            hide_CI=False
        Returns
        -------
        ax
            The ax plot.
    
        """
        if 'xlabel' not in figkwargs:
            figkwargs['xlabel'] = None
        if 'ylabel' not in figkwargs:
            figkwargs['ylabel'] = None
        if 'colorbar_label' not in figkwargs:
            figkwargs['colorbar_label'] = None
        if 'colorbar_axes' not in figkwargs:
            figkwargs['colorbar_axes'] = [0.95, 0.15, 0.01, 0.7]
        if 'cmap' not in figkwargs:
            figkwargs['cmap'] = 'Blues'
        if 'cmap_reversed' not in figkwargs:
            figkwargs['cmap_reversed'] = False
        if 'edgecolors' not in figkwargs:
            figkwargs['edgecolors'] = 'face'
        if 'figsize' not in figkwargs:
            figkwargs['figsize'] = (6.4,4.8)
        
        x,xlabel,row_names = SimplePlots.return_array(x,
                                               data,
                                               variable_label=figkwargs['xlabel'])
        y,ylabel,column_names = SimplePlots.return_array(y,
                                                          data,
                                                          variable_label=figkwargs['ylabel'])
        colorby,colorbar_label,_ = SimplePlots.return_array(colorby,
                                                    data,
                                                    variable_label=figkwargs['colorbar_label'])
        annotate,_,_ = SimplePlots.return_array(annotate,
                                                 data,
                                                 variable_label=None)
        color,scalar_mappable = SimplePlots.get_color_pallete(colorby,
                                                               figkwargs['cmap'],
                                                               figkwargs['cmap_reversed'])
        
        if adjust_covar is not None:
            for key,covariates in adjust_covar.items():
                    cat_independentVar_cols = [independentVar for independentVar in covariates if data[independentVar].dtype == 'object']
                    cont_independentVar_cols = [independentVar for independentVar in covariates if data[independentVar].dtype != 'object']
                    if len(cat_independentVar_cols) == 0:
                        cat_independentVar_cols = None
                    if len(cont_independentVar_cols) == 0:
                        cont_independentVar_cols = None
                    if key == 'x':
                        adj_x = stats.MassUnivariate.adjust_covariates_with_lin_reg(df=data,
                                                                                            cat_independentVar_cols=cat_independentVar_cols,
                                                                                            cont_independentVar_cols=cont_independentVar_cols,
                                                                                            dependentVar_cols=x)
                        x = adj_x.values
                        if xlabel is not None:
                            if isinstance(xlabel,list):
                                xlabel=[f'Adj. {i}' for i in xlabel]
                            elif isinstance(xlabel,str):
                                xlabel = f'Adj. {xlabel}'
                    elif key== 'y':
                        adj_y = stats.MassUnivariate.adjust_covariates_with_lin_reg(df=data,
                                                                                            cat_independentVar_cols=cat_independentVar_cols,
                                                                                            cont_independentVar_cols=cont_independentVar_cols,
                                                                                            dependentVar_cols=y)
                        y = adj_y.values
                        if ylabel is not None:
                            if isinstance(ylabel,list):
                                ylabel = [f'Adj. {i}' for i in ylabel]
                            elif isinstance(ylabel,str):
                                ylabel = f'Adj. {ylabel}'

        if x.ndim > 1 and y.ndim == 1:
            raise TypeError('Please provide only the following option: x single value, y single value; x single value, y list of values, x list of values and y list of values.')
        
        if x.ndim == 1:
            x = x.reshape(-1, 1)
        
        #SPECIAL CASE 1: when y is defined as a list but x is not a list, e.g., list of strings that corresponds to different columns, then hue is applied.
        multiplot=False
        if y.ndim > 1 and y.shape[1] > 1: #if y is defined as list, then hue is automatically applied
            if not isinstance(column_names,list):
                if isinstance(column_names,str):
                    column_names = [f'{column_names}_{col+1}' for col in range(y.shape[1])]
                else:
                    column_names = [f'Y_{col+1}' for col in range(y.shape[1])]
            if x.ndim > 1:
                if not isinstance(row_names,list):
                    if isinstance(row_names,str):
                        row_names = [f'{row_names}_{row+1}' for row in range(x.shape[1])]
                    else:
                        if xlabel is not None:
                            row_names = [xlabel] if isinstance(xlabel,str) else xlabel
                        else:
                            row_names = [f'X_{row+1}' for row in range(x.shape[1])]
            # return row_names,column_names,x,y
            row_columns = np.asarray([(row_names[i],column_names[n],x[idx,i],y[idx,n]) for i in range(len(row_names)) for n in range(len(column_names)) for idx in range(y.shape[0])])
            
            data = pd.DataFrame(row_columns)
            data.columns = ['X_label','Y_label','x','y']
            data['x'] = data['x'].astype('float64')
            data['y'] = data['y'].astype('float64')
            multiplot=True
        
        if y.ndim == 1:
            y = y.reshape(-1, 1)
        
        if 'legend_loc' not in figkwargs:
            figkwargs['legend_loc'] = 'outside'    
        if 'linewidth' not in figkwargs:
            figkwargs['linewidth'] = 1.5
        if 'markersize' not in figkwargs:
            figkwargs['markersize'] = 1.5
        if 'fontsize' not in figkwargs:
            figkwargs['fontsize'] =10
        if 'hide_CI' not in figkwargs:
            figkwargs['hide_CI'] = False
        
        def plotting(x,
                     y,
                     color=None,
                     annotate=annotate, 
                     unique_label=None, 
                     combined=False, 
                     scaling=scaling,
                     edgecolors=figkwargs['edgecolors'],
                     return_stats=return_stats,
                     ax=ax):
            #calculating the mass univariate
            model, _ = stats.MassUnivariate.mass_univariate(
                cont_independentVar_cols=x,
                dependentVar_cols=y,
                scaling=scaling
                )  # will perform standaridzation inside the function
            # get the beta and calculate p-value for the regression model
            y_pred = model.predict({f'Cont_{i}':x[:,i] for i in range(x.shape[1])}) # most likely will be Cont_0. Because there is only one variable of x anyway. y_pred is returned as pd.Series
            #y_pred = model.predict(sm.add_constant(x),transform=False) #transform is used with ols but not OLS.
            predictions = model.get_prediction()
            df_predictions = predictions.summary_frame()
            if all(item.dtype == 'O' for item in x):
                raise TypeError('The items passed to X are categorical, i.e. strings. you must instead create dummy variable and pass that instead. Maybe use pd.get_dummy')
            sorted_x = np.argsort(x[:, 0])
            coefs = model.params.values[1]
            p_value = model.pvalues.values[1]
            if scaling == 'both':
                x = StandardScaler().fit_transform(x)
                y = StandardScaler().fit_transform(y)
            elif scaling == 'x':
                x = StandardScaler().fit_transform(x)
            elif scaling == 'y':
                y = StandardScaler().fit_transform(y)
            if unique_label is None:
                #calculate the correlation label
                corr_label = r'$r$=%0.03f, pval = %0.02e' % (coefs, p_value)
                
                if not combined:
                    ax.scatter(x[:, 0], y,c=color,s=figkwargs['markersize'],edgecolors=edgecolors)
                    if return_stats:
                        ax.plot(x[sorted_x, 0], y_pred[sorted_x], '-', label=corr_label,linewidth=figkwargs['linewidth'])
                    if annotate is not None:
                        for text_id,text in enumerate(annotate):
                            ax.annotate(text,(x[text_id,0],y[text_id]))
                else:
                    ax.plot(x[:, 0], y, 'o', label='total',alpha=.01,markersize=figkwargs['markersize'])
                    handles, labels = ax.get_legend_handles_labels()
                    ax.plot(x[sorted_x, 0], y_pred[sorted_x], '-',
                        label=corr_label, color=handles[len(handles)-1].get_color(),linewidth=figkwargs['linewidth'])
                if not figkwargs['hide_CI']:
                    ax.fill_between(x[sorted_x, 0], df_predictions.loc[sorted_x, 'mean_ci_lower'], df_predictions.loc[sorted_x,
                                    'mean_ci_upper'], linestyle='--', alpha=.1, color='crimson', label=unique_label)
    
            else:
                corr_label = r'$r$=%0.03f, pval = %0.02e' % (coefs, p_value)
                ax.plot(x[:, 0], y, '.', label=unique_label,markersize=figkwargs['markersize'])
                handles, labels = ax.get_legend_handles_labels()
                ax.plot(x[sorted_x, 0], y_pred[sorted_x], '-',
                        label=corr_label, color=handles[len(handles)-1].get_color(),linewidth=figkwargs['linewidth'])
                if not figkwargs['hide_CI']:
                    ax.fill_between(x[sorted_x, 0], df_predictions.loc[sorted_x, 'mean_ci_lower'], df_predictions.loc[sorted_x,
                                    'mean_ci_upper'], linestyle='--', alpha=.1, color='crimson')
        set_label=True
        if multiplot:
            assert hue is None, 'too complicated, cannot have hue'
            if plot_type == 'grid': # x vs. y                    
                if ax is None:
                    fig,axes = plt.subplots(len(column_names),len(row_names),figsize=figkwargs['figsize'],sharex=True,sharey=True)
                    axes = axes.flatten()
                else:
                    axes = ax
                    if isinstance(axes,np.ndarray):
                        if axes.ndim == 2:
                            axes = axes.flatten()
                            assert all(isinstance(ax,plt.Axes) for ax in axes), 'Not all of your figure are of plt.Axes type'
                    assert len(axes) == len(column_names)*len(row_names), 'Number of ax provided do not match the number of plot you want'
                for idx,((col,row),ax) in enumerate(zip(product(column_names,row_names),axes)):
                    temp_data = data[(data['X_label']==row) & (data['Y_label']==col)]
                    temp_x = np.array(temp_data['x']).reshape(-1,1)
                    temp_y = np.array(temp_data['y']).reshape(-1,1)
                    plotting(temp_x,temp_y,scaling=scaling,ax=ax)
                    temp_xlabel = f'standardize({row})' if scaling=='both' or scaling=='x' else row
                    temp_ylabel = f'standardize({col})' if scaling=='both' or scaling=='x' else col
                
                    if idx%len(row_names)==0: #set ylabel
                        ax.set_ylabel(temp_ylabel,fontsize=figkwargs['fontsize'])    
                    if idx>=(len(row_names)*(len(column_names)-1)):
                        ax.set_xlabel(temp_xlabel,fontsize=figkwargs['fontsize'])
                    
                    SimplePlots.plot_legend_loc(ax,return_stats=return_stats,plot_legend=True,**figkwargs)
                    
                figkwargs['legend'] = False
                set_label = False
            elif plot_type == 'combined':
                assert len(row_names) == 1, 'Cannot do combined plot if there are multiple values on both axes, only multiple values on the y argument and single value on x argument'
                if ax is None:
                    fig,ax = plt.subplots(figsize=figkwargs['figsize'])
                else:
                    assert isinstance(ax,plt.Axes), 'You have provided more than one subplot'
                data = data.reset_index(drop=True)
                unique_hues = data['Y_label'].unique()
                for idx, unique_hue in enumerate(unique_hues):
                    temp_data = data[data['Y_label'] == unique_hue]
                    temp_x = np.array(temp_data['x']).reshape(-1,1)
                    temp_y = np.array(temp_data['y']).reshape(-1,1)
                    plotting(temp_x, temp_y,
                            unique_label=unique_hue,scaling=scaling,ax=ax)
                if combined:
                    plotting(x,y,combined=True,scaling=scaling,ax=ax)
                    
        if isinstance(hue,str):
            assert isinstance(data,pd.DataFrame), 'dataframe is missing'
            assert not multiplot, 'too complicated, cannot have hue and multiple value on y argument'
            if ax is None:
                fig,ax = plt.subplots(figsize=figkwargs['figsize'])
            else:
                assert isinstance(ax,plt.Axes), 'You have provided more than one subplot'
            data = data.reset_index(drop=True)
            unique_hues = data[hue].unique()
            for idx, unique_hue in enumerate(unique_hues):
                temp_data = data[data[hue] == unique_hue].index.to_list()
                plotting(x[temp_data], y[temp_data],
                         unique_label=unique_hue,scaling=scaling,ax=ax)
            if combined:
                plotting(x,y,combined=True,scaling=scaling,ax=ax)
        
        else:
            if not multiplot:
                if ax is None:
                    fig,ax = plt.subplots(figsize=figkwargs['figsize'])
                else:
                    assert isinstance(ax,plt.Axes), 'You have provided more than one subplot'
                plotting(x,y,scaling=scaling,ax=ax)
        
        if set_label:
            xlabel=f'standardize({xlabel[0]})' if scaling=='both' or scaling=='x' else xlabel[0]
            ylabel=f'standardize({ylabel[0]})' if scaling=='both' or scaling=='y' else ylabel[0]
            if ylabel != 'standardize(None)':
                ax.set_ylabel(ylabel,fontsize=figkwargs['fontsize'])
            ax.set_xlabel(xlabel,fontsize=figkwargs['fontsize'])
            
        if figkwargs['colorbar_label'] is not None:
            if fig is None:
                raise ValueError('Fig has not been defined. Either provide a fig argument, or do not provide ax argument')
            if color is None:
                raise AttributeError('you have not defined colorby and you want to have a color label')
            cbar_ax = fig.add_axes(figkwargs['colorbar_axes'])
            cbar = ax.figure.colorbar(scalar_mappable, cax=cbar_ax)
            cbar.set_label(figkwargs['colorbar_label'], size=12)
        
        if 'legend' not in figkwargs:
            figkwargs['legend'] = True
        SimplePlots.plot_legend_loc(ax,return_stats=return_stats,plot_legend=figkwargs['legend'],**figkwargs)

        if not multiplot or plot_type != 'grid': 
            ax.set_title(title)
        if multiplot and plot_type == 'grid':
            if fig is None:
                raise ValueError('Fig has not been defined. Either provide a fig argument, or do not provide ax argument')
            fig.suptitle(title)
        

    def Box(x: Union[np.ndarray,pd.DataFrame,pd.Series,list,str],
            y: Union[np.ndarray, pd.DataFrame, pd.Series,list, str],
            separateby:Union[np.ndarray,pd.DataFrame,pd.Series,list,str]=None,
            hue: Union[np.ndarray,pd.DataFrame,pd.Series,list,str] = None,
            order:Optional[Union[list,str]]=None,
            data: Optional[pd.DataFrame] = None,
            title:Optional[str] = None,
            fig:Optional[plt.Figure] = None,
            ax:Optional[plt.Axes] = None,
            adjust_covar:dict = None,
            **figkwargs) -> Optional[plt.Axes]:
        
        xlabel=figkwargs.get('xlabel',None)
        ylabel=figkwargs.get('ylabel',None)
        
        #this returns an array
        x,xlabel,_ = SimplePlots.return_array(x,data=data,variable_label=xlabel,must_be='str')
        y,ylabel,_ = SimplePlots.return_array(y,variable_label=ylabel,data=data)
        separateby,plot_label,_ = SimplePlots.return_array(separateby,data=data,must_be='str')
        hue,hue_legend_label,_ = SimplePlots.return_array(hue,data = data,must_be='str')
        
        #ax.boxplot takes in a list of lists.
        separateby = [None for i in range(len(x))] if separateby is None else separateby
        hue = [None for i in range(len(x))] if hue is None else hue
        
        if adjust_covar is not None:
            if 'x' in adjust_covar:
                cat_independentVar_cols = [independentVar for independentVar in adjust_covar['x'] if data[independentVar].dtype == 'object']
                cont_independentVar_cols = [independentVar for independentVar in adjust_covar['x'] if data[independentVar].dtype != 'object']
                if len(cat_independentVar_cols) == 0:
                    cat_independentVar_cols = None
                if len(cont_independentVar_cols) == 0:
                    cont_independentVar_cols = None
                adj_x = stats.MassUnivariate.adjust_covariates_with_lin_reg(
                    df=data,
                    cat_independentVar_cols=cat_independentVar_cols,
                    cont_independentVar_cols=cont_independentVar_cols,
                    dependentVar_cols=x
                    )
                x = adj_x.values.reshape(-1)
                if xlabel is not None:
                    xlabel = f'Adj. {xlabel}'
            if 'y' in adjust_covar:
                cat_independentVar_cols = [independentVar for independentVar in adjust_covar['y'] if data[independentVar].dtype == 'object']
                cont_independentVar_cols = [independentVar for independentVar in adjust_covar['y'] if data[independentVar].dtype != 'object']
                if len(cat_independentVar_cols) == 0:
                    cat_independentVar_cols = None
                if len(cont_independentVar_cols) == 0:
                    cont_independentVar_cols = None
                adj_y = stats.MassUnivariate.adjust_covariates_with_lin_reg(
                    df=data,
                    cat_independentVar_cols=cat_independentVar_cols,
                    cont_independentVar_cols=cont_independentVar_cols,
                    dependentVar_cols=y
                    )
                y = adj_y.values.reshape(-1)
                if ylabel is not None:
                    if isinstance(ylabel,list):
                        ylabel = [f'Adj. {i}' for i in ylabel]
                    elif isinstance(ylabel,str):
                        ylabel = f'Adj. {ylabel}'        
        #you want to groupby x in case x is not unique.
        to_plot_dictionary = SimplePlots.Groupby.groupby(separateby,x,hue,y=y)
        if isinstance(order,list):
            if not all(isinstance(item,str) for item in order):
                raise TypeError('order must be list of strings')
            for x_val in order:
                if x_val not in np.unique(x):
                    raise ValueError('the value in the order does not exist in x-value')
            for x_val in np.unique(x):
                if x_val not in order:
                    raise ValueError('you must specify the order of all x values')
            to_plot_dictionary = {separateby: {keys:to_plot_dictionary[separateby][keys] for keys in order} for separateby in to_plot_dictionary.keys()}
        
        # If you are comparing sex by three conditions . Here, sex label is on 
        # the x axis, and at each positions, are three conditions (i.e. hue). 
        # The argument to pass to the ax.boxplot is:
        # if data to plot at each x position is y[x] and to plot at each hue 
        # position is y[x][hue]
        # then list to pass to the ax.boxplot is: [[y[x1][hue1],y[x2][hue1],
        # y[x3][hue1]...],[y[x1][hue2],y[x2][hue2],y[x3][hue2],...]...]
        
        #sort the values is needed if doing hue.
        # sort_indices_in_x = np.argsort(x)
        # x = x[sort_indices_in_x]
        # separateby = separateby[sort_indices_in_x]
        # hue = hue[sort_indices_in_x]
        # colorby = [colorby[i] for i in sort_indices_in_x]
        # y = [y[i] for i in sort_indices_in_x]
        
        #first level of to_plot_dictionary is separateby. If there is none,
        #then the key is None.
        unique_x = to_plot_dictionary[list(to_plot_dictionary.keys())[0]].keys()
        x_pos = len(unique_x)
        x_pos = np.arange(1,x_pos+1)
        
        ######### figkwargs ##############
        
        cmap=figkwargs.get('cmap','coolwarm')
        cmap_reversed=figkwargs.get('cmap_reversed',False)
        figsize=figkwargs.get('figsize',None)
        fontsize=figkwargs.get('fontsize',10)
        box_plots_kwargs = dict()
        box_plots_kwargs['sym'] = figkwargs.get('sym','gD')
        box_plots_kwargs['widths'] = figkwargs.get('widths',0.6)
        box_plots_kwargs['patch_artist']=figkwargs.get('patch_artist',False)
        box_plots_kwargs['notch']=figkwargs.get('notch',False)
        box_plots_kwargs['medianprops'] = figkwargs.get('medianprops',dict(color='grey'))
        box_plots_kwargs['vert'] = figkwargs.get('vert',True)
        box_plots_kwargs['whis'] = figkwargs.get('whis',1.5)
        box_plots_kwargs['bootstrap'] = figkwargs.get('bootstrap',None)
        box_plots_kwargs['usermedians'] = figkwargs.get('usermedians',None)
        box_plots_kwargs['conf_intervals'] = figkwargs.get('conf_intervals',None)
        legend_label = dict()
        legend_label['loc'] =  figkwargs.get('legend_loc','upper right')
        rotation_x = figkwargs.get('rotation_x',0)

        ######### figkwargs:end ##############
        
        if not all(item is None for item in to_plot_dictionary.keys()): # the first level is separateby
            uniq_separateby = list(to_plot_dictionary.keys())
            if len(uniq_separateby)>3:
                row = int(np.ceil(len(uniq_separateby)/3))
                column = 3
            else:
                row =1
                column = len(uniq_separateby)
            fig,axes = plt.subplots(row,column,sharex=True,sharey=True,figsize=figsize)
            if isinstance(axes,plt.Axes):
                axes = [axes]
            else:
                if len(axes) > 1:
                    axes = axes.flatten()
                else:
                    axes = [axes]
        else:
            row = 1
            column = 1
            if ax is None:
                fig, ax = plt.subplots(figsize=figsize)
            axes = [ax]

        if not all(item is None for item in hue):
            pal = sns.color_palette(cmap,len(np.unique(hue)))
            my_cmap = ListedColormap(pal)
            sm = plt.cm.ScalarMappable(cmap=my_cmap)
            sm.set_array([])
            color = np.array(pal)
        
        def plot_group_box(to_plot,ax,color):
            y_hue = [list(to_plot[i].values()) for i in to_plot.keys()]
            label_list = list(to_plot[list(to_plot.keys())[0]].keys())
            width = 1/len(label_list)
            box_plots_kwargs['widths'] = width
            xlocations  = [ x*((1+ len(y_hue))*width) for x in range(len(label_list))]
            space = len(y_hue)/2                    
        
            # --- Offset the positions per group:
            group_positions = []
            for num, dg in enumerate(y_hue):
                _off = (0 - space + (0.5+num))
                group_positions.append([x+_off*(width+0.01) for x in xlocations])
            
            hue_legends = []
            for dg, pos,c in zip(y_hue, group_positions,color):
                boxes = ax.boxplot(dg,
                            labels=label_list,
                            positions=pos,
                            boxprops=dict(color=c),
                            capprops=dict(color=c),
                            whiskerprops=dict(color=c),
                            flierprops=dict(color=c, markeredgecolor=c),                       
                            **box_plots_kwargs
                            )
                hue_legends.append(boxes['boxes'][0])
            ax.legend(hue_legends,[i for i in to_plot.keys()],**legend_label)
            ax.set_xticks(xlocations)
            ax.set_xticklabels(label_list,rotation=rotation_x)
        for idx, ax in enumerate(axes):
            if not all(item is None for item in separateby):
                for separate_key in to_plot_dictionary.keys():    
                    if not all(item is None for item in hue):
                        unique_hues = np.unique(hue)
                        to_plot = {h: {x_:to_plot_dictionary[separate_key][x_][h]['y'] for x_ in unique_x } for h in unique_hues}
                        plot_group_box(to_plot,ax,color)
                    else:
                        to_plot = {k1:v1[None]['y'] for k1,v1 in to_plot_dictionary[separate_key].items()}
                        ax.boxplot(to_plot.values(),
                                    positions=x_pos,labels=to_plot.keys(),**box_plots_kwargs)
                if idx%3==0:
                    ax.set_ylabel(ylabel,fontsize=fontsize)

                
            else:
                if not all(item is None for item in hue):
                    unique_hues = np.unique(hue)
                    to_plot = {h: {x_:to_plot_dictionary[None][x_][h]['y'] for x_ in unique_x } for h in unique_hues}
                    plot_group_box(to_plot,ax,color)

                else:
                    to_plot = {k1:v1[None]['y'] for k1,v1 in to_plot_dictionary[None].items()}
                    ax.boxplot(to_plot.values(),
                                positions=x_pos,labels=to_plot.keys(),**box_plots_kwargs)
                
                ax.set_ylabel(ylabel,fontsize=fontsize)
                ax.set_title(title)
        if len(axes)>1:
            fig.suptitle(
                title,
                size='xx-large')
        
            
        
        
# def draw_box_plots(df,
#                    dependentVar=None,
#                    independentVar=None,
#                    threshold=None,
#                    percentage=0.2,
#                    ancestry_PCs=None,
#                    ylabel=None,ax=None):
#     """
#     draw box plots by dividing the dataset into high and low risk
#     """
#     if not independentVar:
#         measure = np.asarray(df[dependentVar])
#     else:
#         measure = stats.MassUnivariate.adjust_covariates_with_lin_reg(np.asarray(
#             df[dependentVar]), StandardScaler().fit_transform(df[independentVar]))

#     high_risk, low_risk = stats.divide_high_low_risk(stats.MassUnivariate.adjust_covariates_with_lin_reg(
#         np.asarray(df[threshold]), StandardScaler().fit_transform(df[ancestry_PCs])), low_perc=percentage, high_perc=percentage)

#     measure_df = pd.DataFrame({'measure': measure.reshape(-1), 'risk': [
#                               'high risk' if i in high_risk else 'low risk' if i in low_risk else np.nan for i in range(len(measure))]}).dropna()
#     stats, pval = ttest_ind(measure_df[measure_df['risk'] == 'low risk']['measure'],
#                             measure_df[measure_df['risk'] == 'high risk']['measure'], equal_var=True)
#     low_risk_mean = measure_df[measure_df['risk']
#                                == 'low risk']['measure'].mean(axis=0)
#     high_risk_mean = measure_df[measure_df['risk']
#                                 == 'high risk']['measure'].mean(axis=0)

#     sns.boxplot(x='risk', y='measure', data=measure_df,ax=ax)
#     if not independentVar:
#         ax.set_ylabel(ylabel)
#     else:
#         ax.set_ylabel('corrected ' + ylabel)
#     ax.text(0, 0, 't-test pval=%0.03f' % (pval))

class Brainmap:
    """
    This is used to plot the brain visualisations using nibable
    
    Attributes:
        atlas_file = the nibabel loaded image
        atlas = the numpy array representation of nifti image
        cmap = the color scheme
        
    Methods:
        get_edges
            used to get the visualise the segmentation outline
        plot_segmentation
            plot the segmentations with filled in color and legend
        get_ROIs_coordinates
            get the X,Y,Z coordinates of different regions in the Nifti file.
    """
    def __init__(self,atlas_file:Union[str,nib.nifti1.Nifti1Image],
                 cmap:str='Spectral',cmap_reversed:bool=False)-> None:
        """
        Parameters
        ----------
        atlas_file : Union[str,nib.nifti1.Nifti1Image]
            The path to the Nifti file or the nibable loaded nifti image.
        cmap : str, optional
            The color scheme. The default is 'Spectral'.
        cmap_reversed : bool, optional
            Reverse the color scheme. The default is False.

        """
        if isinstance(atlas_file,str):
            self.atlas_file = nib.load(atlas_file)
        elif isinstance(atlas_file,nib.nifti1.Nifti1Image):
            self.atlas_file = atlas_file
        atlas_affine = self.atlas_file.affine
        if nib.aff2axcodes(atlas_affine) != ('R','A','S'): # if it is not RAS orientation, change to it.
            self.atlas_file = nib.as_closest_canonical(self.atlas_file)
        self.atlas = self.atlas_file.get_fdata()
        self.cmap = copy.copy(plt.cm.get_cmap(cmap))
        self.cmap.set_bad(alpha=0) # set transparency of np.nan numbers into 0
        if cmap_reversed:
            self.cmap = self.cmap.reversed()
    
    @staticmethod
    def get_edges(outline:np.ndarray): # use in brain_segmentation
        """
        Draw the edges of a structure.
        Parameters
        ----------
        outline:np.ndarray : 
            array of number, edges will be drawn around the edges of the non-zero structures.
            If two pixels next to each other are non-zero, then a black rectangle is drawn.
            If two pixels are non-zero and not next to each other, then two black squares are drawn.
        Returns
        -------
        None.

        """
        edges = [] #for each pixel colour the edges.
        rr,cc = np.nonzero(outline)
        switcheroo = lambda x,y: (y,x) # the imshow and the np.matrix have different coordinates
        def check_sides(r,c,outline):
            sides = {'top':False,'bottom':False,'left':False,'right':False}
            #the key is visualise that the 0,0 of the numpy matrix is upper left.
            if r == 0 or not outline[r-1,c]:
                # top edge
                sides['top'] = True
            if r == outline.shape[0] -1 or not outline[r+1,c]:
                # bottom edge
                sides['bottom'] = True
            if c == 0 or not outline[r,c-1]:
                # left edge
                sides['left'] = True
            if c == outline.shape[1]-1 or not outline[r,c+1]:
                # right edge
                sides['right'] = True
            return sides
        
        for r,c in zip(rr,cc):
            ul_coord = switcheroo(r,c) # upper left
            ll_coord = switcheroo(r+1,c) # lower left
            ur_coord = switcheroo(r,c+1) # upper right
            lr_coord = switcheroo(r+1,c+1)# lower right
            
            sides_dict = check_sides(r,c,outline)
            if sides_dict['top'] == True:
                edges.append([ul_coord,ur_coord])# top edge
            if sides_dict['bottom'] == True:
                edges.append([ll_coord,lr_coord])# bottom edge
            if sides_dict['left'] == True:
                edges.append([ul_coord,ll_coord])# left edge
            if sides_dict['right'] == True:
                edges.append([ur_coord,lr_coord])# right edge

        return np.array(edges)-0.5
    
    @classmethod
    def plot_segmentation(cls,
                         map_view:List=['all'],
                         atlas_slice:Union[int,list,dict]=None,
                         regions_to_hide:list=None,
                         plot_values:dict=None,
                         plot_values_threshold:float=None,
                         mask:dict=None,
                         fig:mpl.figure.Figure=None,
                         axes:Union[np.ndarray,List,plt.Axes]=None,
                         colorbar:bool=False,
                         label_legend:dict=None,
                         label_legend_colours:dict=None,
                         legends:bool=True,
                         atlas_file:Union[str,nib.nifti1.Nifti1Image]=None,
                         cmap:str='Spectral',plot_orientation:bool=True,
                         plot_focus=False,
                         remove_background=True,
                         T2=False,
                         **figkwargs):
        """
        Plot the brain segmentation
        
        Note:
            Essentially, two brain maps are created.
            The original brain map is used to create segmentation outline.
            The second brain map is used to fill in the color.
            
        Parameters
        ----------
        map_view : List, optional
            {'all','sagittal','axial','coronal'}. The default is ['all'].
        atlas_slice: int,list, dict, optional
            dictionary keys: axial, coronal, sagittal, values = slice number
            if list: three numbers corresponds to axial, coronal, sagittal
            Choose which slice to show, else middle slice will be shown.
        regions_to_hide : list, optional
            Give the list of regions to hide (the regions must be list of intergers) The labels will be set to transparency 0. The default is None.
        plot_values : Union[dict], optional
            plot a color for each label denoting the strength of p-value or some other metrics.
            If provide a dictionary, the key will be the label, and the value will be the value. The default is None.
        plot_values_threshold:float, optional
            A number that can be applied to plot_values and set the ones that do not pass the threshold to np.nan
        mask : Union[dict], optional
            Can pass a mask, that after passing the plot_values threshold, instead of plotting the original plot_values, the mask will be plotted instead.
            E.g. I have p-values as plot_values, but I want to plot beta- coefficients that has p-value <0.05 instead. Here the dict of beta coef is the mask.
        fig : mpl.figure.Figure, optional
            Can specify the fig, if not fig will be created. The default is None.
        axes : Union[np.ndarray,List], optional
            Can provide the specific axes, list of axes. If not axes will be created. The default is None.
        colorbar : bool, optional
            If plot_values is specified, then can choose if to plot the colorbar. The default is False.
        label_legend : dict, optional
            If not using the plot_values, but you want to show the segmentation.
            Each color patch in the legend will correspond to the color in the plot
            Must provide a dictionary, where the key is interger denoting the label.
            And value is the string abbreviation. The default is None.
        label_legend_colours: dict, optional
            If providing label_legend, and if you are performing multiple subplots. It may be good idea, to use this to have consistent colours.
            Must provide a dictionary, where the key is interger denoting the label, and value is the colour.
        legend: bool, optional
            Whether to plot the brain legend.
            The default is True
        atlas_file : Union[str,nib.nifti1.Nifti1Image], optional
            The path to the nifti file, or the nib.load(Nifti file). The default is None.
        cmap : str, optional
            The color scheme. The default is 'Spectral'.
        plot_orientation: bool, optional
            If you want to plot the axis in the RAS coordinate.
        T2: bool, default False.
            If the input nii.gz image is not a parcellation image. Take care with the background value.
        **figkwargs : TYPE
            cmap_reversed = if you want to revese the cmap default False
            cb_orientation = {'horizontal','vertical'} if you want your change your colorbar orientation. Default horizontal next to the last axes.
            cb_title = str. name of the colorbar
            cb_threshold_greater=True, if you want the threshold to be greater or lower
            cb_vmin,cb_vmax = define the colorscale of the colorbar
            figsize = Default (20,10)
            outline_label_legends: bool. Default True. 
                The outline is updated if the the same legend is found in two regions.
                If False, regions not hidden by regions_to_hide is still outlined.
                If True, regions not hiddend by regions_to_hide is not outlined.
            outline_regions_to_hide: bool. Default True. The outline is not updated after using regions_to_hide. 
            label_legend_bbox_to_anchor:(-2.5, -1,0,0)
            label_legend_ncol : 6
            label_legend_loc: 'lower left'
            label_legend_fontsize: 'medium' or float
            label_legend_axis : plt.Axis
            image_alpha: 1
            background_value: Default 0. We set any value in the image <= background value to np.nan (transparent)
            
        Raises
        ------
        ValueError
            DESCRIPTION.
        AttributeError
            DESCRIPTION.

        Returns
        -------
        fig : TYPE
            The mpl.Figure either created or used.
        map_view_dict : TYPE
            a dictionary containing all atlas array, including 'im' plotted.
        """
        if 'cmap_reversed' not in figkwargs:
            figkwargs['cmap_reversed'] = False
        brain_map = cls(atlas_file,cmap,figkwargs['cmap_reversed'])
        figkwargs['background_value'] = 0 if 'background_value' not in figkwargs else figkwargs['background_value'] # some images have weird artefacts.
        x,y,z = brain_map.atlas.shape
        max_dim = max(x,y,z)
        if 'padding' not in figkwargs:
            figkwargs['padding']=True
        if figkwargs['padding']:
            padding_x = max_dim - x
            padding_y = max_dim - y
            padding_z = max_dim - z
        else:
            padding_x,padding_y,padding_z = 0,0,0
        ##added padding around the 3D array so when plotting the subplots are squared and of equal heights
        brain_map.atlas = np.pad(brain_map.atlas,
                                 [(padding_x//2,padding_x//2),
                                  (padding_y//2,padding_y//2),
                                  (padding_z//2,padding_z//2)],
                                 constant_values=figkwargs['background_value'])
        if remove_background:
            brain_map.atlas[brain_map.atlas <= figkwargs['background_value']] = np.nan # set the background to 0 transparency
        #the following original atlas are needed for the outline.        
        if isinstance(atlas_slice, tuple) or isinstance(atlas_slice,list):
            if len(atlas_slice)!=3:
                raise ValueError("atlas slice must be 3, stands for x, y, z coordinates. \
                        x- moves the sagittal slice (i.e., L-R axis),\
                        y-moves the coronal slice (i.e., AP axis) \
                        z- moves the axial slice (i.e., S-I axis)")
        else:
            atlas_slice = (x//2,y//2,z//2)
        atlas_slice_dict = dict(zip(['sagittal','coronal','axial'],atlas_slice))
        atlas_slice_dict['axial'] += padding_z//2
        atlas_slice_dict['coronal'] += padding_y//2
        atlas_slice_dict['sagittal'] += padding_x//2
        
        # elif isinstance(atlas_slice,dict):
        #     for key,value in atlas_slice.items():
        #         atlas_slice_dict[key] = value                
        
        #original atlases are used to delineate the outline
        original_axial_atlas = brain_map.atlas[:,:,atlas_slice_dict['axial']].copy()
        original_coronal_atlas = brain_map.atlas[:,atlas_slice_dict['coronal'],:].copy()
        original_sagittal_atlas = brain_map.atlas[atlas_slice_dict['sagittal'],:,:].copy()
        
        # the following regions need to be hidden (but outline will still be shown)
        if regions_to_hide is not None:
            for region in regions_to_hide:
                brain_map.atlas[brain_map.atlas == region] = np.nan
                if 'outline_regions_to_hide' not in figkwargs:
                    figkwargs['outline_regions_to_hide'] = True
                if not figkwargs['outline_regions_to_hide']:
                    original_axial_atlas = brain_map.atlas[:,:,atlas_slice_dict['axial']].copy()
                    original_coronal_atlas = brain_map.atlas[:,atlas_slice_dict['coronal'],:].copy()
                    original_sagittal_atlas = brain_map.atlas[atlas_slice_dict['sagittal'],:,:].copy()
            
        if label_legend is not None:# if legend dictionary is provided
            if not isinstance(label_legend,dict):
                raise TypeError('label_legend needs to be a dictionary, where keys are the label, and values are the string values')
            unique_regions = np.unique(brain_map.atlas[~np.isnan(brain_map.atlas)]) #not labelling the np.nan values
            for region in unique_regions:
                if region not in label_legend:
                    brain_map.atlas[brain_map.atlas==region] = np.nan #regions that are not provided in the legend they are removed from colouring.
            
            #check for unique legends- basically group the labels/ regions if the legend is the same. the original outline will still be shown
            unique_legends = set(label_legend.values()) 
            #essentially if 2 keys denote the same value, you get a new dictionary: {Value:[key1,key2,etc.]}
            legend_label = {uniq_leg:[k for k in label_legend.keys() if label_legend[k] == uniq_leg] for uniq_leg in unique_legends}
            for legend,label in legend_label.items():
                if len(label)>1:
                    for region in label:
                        #if more than one key show the same value, then change it to the same key.
                        brain_map.atlas[brain_map.atlas==region] = label[0]
            
            ####setting vmin vmax - this is needed to get common colours across multiple plots
            # the colours are not in sequential order. For example, number 5 and 79 denotes the same structures.
            
            #####ploting label legends####
            def find_closest_name(col):
                #taken from here
                #https://stackoverflow.com/questions/71756150/getting-the-names-of-colors-from-matplotlib-colormap-object
                #This function is used to get the name from to_rgb function
                rv, gv, bv = to_rgb(col)
                min_colors = {}
                for col in CSS4_COLORS:
                    rc, gc, bc = to_rgb(col)
                    min_colors[(rc - rv) ** 2 + (gc - gv) ** 2 + (bc - bv) ** 2] = col
                closest = min(min_colors.keys())
                return min_colors[closest], np.sqrt(closest)
            
            if label_legend_colours is None:
                label_val = list(set(label_legend.values()))
                n_colors = len(label_val)
                vals = np.linspace(0, 1, n_colors)
                label_legend_colours_inversed = {k:find_closest_name(brain_map.cmap(val))[0] for k,val in zip(label_val,vals)} # {'temporal':[0,0,0],'parietal':[0.1,0.2,0.3],...}
                label_legend_colours = {k:label_legend_colours_inversed[v] for k,v in label_legend.items()} #{5:[0.1,0.2,0.3],6:[1,2,3],...}
                # brain_map.cmap = LinearSegmentedColormap.from_list('from_list',
                #                                  [(val, col) for val, col in zip(vals, label_legend_colours.values())])

            if not isinstance(label_legend_colours,dict):
                raise TypeError('label_legend_colours need to be dictionary')
            
            if all(isinstance(v,str) for v in label_legend_colours.values()):
                label_legend_colours = {k:np.array(to_rgb(v)) for k,v in label_legend_colours.items()}
            
            if not all(isinstance(v,np.ndarray) for v in label_legend_colours.values()):
                raise TypeError('the colours must be defined as either string or np.ndarray. Use matplotlib.colors.to_rgb')
                
            
            if 'outline_label_legends' not in figkwargs: # whether to outline only the keys in the legend
                figkwargs['outline_label_legends'] = True
            if figkwargs['outline_label_legends']:
                original_axial_atlas = brain_map.atlas[:,:,atlas_slice_dict['axial']].copy()
                original_coronal_atlas = brain_map.atlas[:,atlas_slice_dict['coronal'],:].copy()
                original_sagittal_atlas = brain_map.atlas[atlas_slice_dict['sagittal'],:,:].copy()
                
                
        if plot_values is not None:
            if not isinstance(plot_values,dict):
                raise TypeError('plot_values needs to be a dictionary, where keys are the label, and values are the plot values')
            else:
                unique_regions = np.unique(brain_map.atlas[~np.isnan(brain_map.atlas)])
                if plot_values_threshold is not None:
                    figkwargs['cb_threshold_greater'] = True if 'cb_threshold_greater' not in figkwargs else figkwargs['cb_threshold_greater'] 
                    if mask is not None:
                        if not isinstance(mask,dict):
                            raise TypeError('mask needs to be a dictionary, where keys are the label, and values are the plot values')
                        if figkwargs['cb_threshold_greater']:
                            plot_values = {indx:mask[indx] if (indx in plot_values.keys()) and (plot_values[indx]>plot_values_threshold) and (indx in mask.keys()) else np.nan for indx in unique_regions}
                        else:# if you want to plot values < threshold
                            plot_values = {indx:mask[indx] if (indx in plot_values.keys()) and (plot_values[indx]<plot_values_threshold) and (indx in mask.keys()) else np.nan for indx in unique_regions}
                    else:
                        if figkwargs['cb_threshold_greater']:
                            plot_values = {indx:plot_values[indx] if (indx in plot_values.keys()) and (plot_values[indx]>plot_values_threshold) else np.nan for indx in unique_regions}                  
                        else:
                            plot_values = {indx:plot_values[indx] if (indx in plot_values.keys()) and (plot_values[indx]<plot_values_threshold) else np.nan for indx in unique_regions}                  
                else:
                    plot_values = {indx:plot_values[indx] if indx in plot_values.keys() else np.nan for indx in unique_regions}
                for region,value in plot_values.items():
                    brain_map.atlas[brain_map.atlas == region] = value
                    
        if 'figsize' not in figkwargs:
            figkwargs['figsize'] = (22,10)
        
        if axes is None:
            if 'all' in map_view:
                axes = 3
            else:
                axes = len(map_view)
            fig, axes  = plt.subplots(1,axes,figsize=figkwargs['figsize'])
            try:
                len(axes)
            except TypeError:
                axes = np.asarray([axes]) # because when I zip in zip(map_view,axes) I can't zip len of 1? and len(axessubplot) doesnt return anything :)))
        elif isinstance(axes,(list,np.ndarray)):
            if 'all' in map_view:
                if len(axes) != 3:
                    raise ValueError('need 3 axes')
            else:
                if len(map_view) != len(axes):
                    raise ValueError('number of map_view does not match number of axes provided')
            if (fig is None) and (plot_values is not None) and (colorbar is not None):
                raise AttributeError('Need fig element to plot the colorbar')
        elif isinstance(axes,plt.Axes) and len(map_view)==1 and map_view != 'all':
            axes=[axes]
        #
        axial_atlas = brain_map.atlas[:,:,atlas_slice_dict['axial']].copy()
        coronal_atlas = brain_map.atlas[:,atlas_slice_dict['coronal'],:].copy()
        sagittal_atlas = brain_map.atlas[atlas_slice_dict['sagittal'],:,:].copy()

        map_view_dict = defaultdict(dict)
        if 'all' in map_view:
            map_view = ['axial','coronal','sagittal']
        for view,ax in zip(map_view,axes):
            map_view_dict[view]['ax'] = ax
            if view == 'axial':
                map_view_dict[view]['atlas'] = axial_atlas
                map_view_dict[view]['original_atlas'] = original_axial_atlas
            elif view == 'coronal':
                map_view_dict[view]['atlas'] = coronal_atlas
                map_view_dict[view]['original_atlas'] = original_coronal_atlas
            elif view == 'sagittal':
                map_view_dict[view]['atlas'] = sagittal_atlas
                map_view_dict[view]['original_atlas'] = original_sagittal_atlas
        
        #plot the images
        if 'cb_vmin' not in figkwargs and 'cb_vmax' not in figkwargs:
            vmin,vmax = [],[] #needed to define the colorbar
            for view in map_view_dict.keys():
                try:
                    vmin.append(map_view_dict[view]['atlas'][~np.isnan(map_view_dict[view]['atlas'])].min())
                    vmax.append(map_view_dict[view]['atlas'][~np.isnan(map_view_dict[view]['atlas'])].max())
                except ValueError:
                    vmin.append(np.nan)
                    vmax.append(np.nan)
            figkwargs['cb_vmin'] = None if np.isnan(np.min(vmin)) else np.min(vmin)
            figkwargs['cb_vmax'] = None if np.isnan(np.max(vmax)) else np.max(vmax)
        
        for view,ax in map_view_dict.items():
            if 'image_alpha' not in figkwargs:
                    figkwargs['image_alpha'] = 1
            if isinstance(label_legend_colours,dict):
                #if legend with colour is provided. We need to map the colours to the value in the atlas.
                value_to_colour = np.ndarray(shape=(map_view_dict[view]['atlas'].shape[0],map_view_dict[view]['atlas'].shape[1],4))
                for i in range(0, map_view_dict[view]['atlas'].shape[0]):
                    for j in range(0, map_view_dict[view]['atlas'].shape[1]):
                        try:
                            #the fourth dimension is the alpha channel
                            value_to_colour[i][j] = np.concatenate([label_legend_colours[map_view_dict[view]['atlas'][i][j]],[1]])
                        except KeyError:
                            value_to_colour[i][j] = np.array([1,1,1,0])
                    
                map_view_dict[view]['im'] = map_view_dict[view]['ax'].imshow(np.rot90(value_to_colour),alpha=figkwargs['image_alpha'])
            else:
                map_view_dict[view]['im'] = map_view_dict[view]['ax'].imshow(np.rot90(map_view_dict[view]['atlas']),vmin=figkwargs['cb_vmin'],vmax=figkwargs['cb_vmax'],cmap=brain_map.cmap,alpha=figkwargs['image_alpha'])
        
            #plot the outlines
            if not T2:
                temp_original_atlas = map_view_dict[view]['original_atlas']
                for unique_label in np.unique(temp_original_atlas[~np.isnan(temp_original_atlas)]):
                    #if it is that label, draw the outline
                    temp_outline_atlas = temp_original_atlas.copy()
                    temp_outline_atlas[temp_outline_atlas != unique_label] = 0 # if it is not that label, set the pixel to 0
                    temp_outline_atlas[temp_outline_atlas == unique_label] = 1 # basically draw the border where there is pixel value 1
                    if 'outline_colour' not in figkwargs:
                        figkwargs['outline_colour'] = 'k'
                    if 'outline_alpha' not in figkwargs:
                        figkwargs['outline_alpha'] = 1
                    temp_line = LineCollection(cls.get_edges(np.rot90(temp_outline_atlas)), lw=1, color=figkwargs['outline_colour'],alpha=figkwargs['outline_alpha'])
                    map_view_dict[view]['ax'].add_collection(temp_line)
            
        if 'cb_orientation' not in figkwargs:
            figkwargs['cb_orientation'] = 'vertical'
        #add the colorbar?
        
        if colorbar and figkwargs['cb_vmin'] is not None: # the colorbar is added to the last im
            if plot_values is None:
                raise ValueError('need plot value to have colorbar')
            cb = fig.colorbar(map_view_dict[list(map_view_dict)[-1]]['im'],ax = map_view_dict[list(map_view_dict)[-1]]['ax'], orientation = figkwargs['cb_orientation'])
            if 'cb_title' not in figkwargs:
                figkwargs['cb_title'] = None
            if figkwargs['cb_orientation'] == 'vertical':
                cb.ax.set_ylabel(figkwargs['cb_title'],rotation=90,fontsize=12,fontweight='bold')
            elif figkwargs['cb_orientation'] == 'horizontal':
                cb.ax.set_xlabel(figkwargs['cb_title'],rotation=0,fontsize=12,fontweight='bold')
        
        if 'label_legend_bbox_to_anchor' not in figkwargs:
            figkwargs['label_legend_bbox_to_anchor'] = (-2.5, -1,0,0)
        if 'label_legend_ncol' not in figkwargs:
            figkwargs['label_legend_ncol'] = 6
        if 'label_legend_loc' not in figkwargs:
            figkwargs['label_legend_loc'] = 'lower left'
        if 'label_legend_fontsize' not in figkwargs:
            figkwargs['label_legend_fontsize'] = 'medium'
        if 'label_legend_axis' not in figkwargs:
            figkwargs['label_legend_axis'] = None
        if label_legend is not None:
            #to plot legends?
            if legends:
                to_legend = {v1:find_closest_name(v2)[0] for v1,v2 in zip(label_legend.values(),label_legend_colours.values())}
                
                patches = [mpatches.Patch(color=v, label=k) for k, v in to_legend.items()]
                if isinstance(figkwargs['label_legend_axis'],plt.Axes):
                    figkwargs['label_legend_axis'].legend(
                        handles=patches, 
                        bbox_to_anchor=figkwargs['label_legend_bbox_to_anchor'], 
                        loc=figkwargs['label_legend_loc'],
                        ncol=figkwargs['label_legend_ncol'],
                        fontsize = figkwargs['label_legend_fontsize'],
                        frameon=False)
                else:
                    plt.legend(handles=patches, 
                            bbox_to_anchor=figkwargs['label_legend_bbox_to_anchor'], 
                            loc=figkwargs['label_legend_loc'],
                            ncol=figkwargs['label_legend_ncol'],
                            fontsize = figkwargs['label_legend_fontsize'],
                            frameon=False)

        # for view in map_view:
        #     map_view_dict[view]['ax'].spines[['left','right','top','bottom']].set_visible(False)
        #     map_view_dict[view]['ax'].set_xticks([])
        #     map_view_dict[view]['ax'].set_yticks([])
            
        if plot_orientation:
            for view,ax in map_view_dict.items():
                if view == 'axial':
                    map_view_dict[view]['ax'].text(0,map_view_dict[view]['atlas'].shape[1]//2 + 2, 'L',fontsize=15,fontweight='bold')
                    map_view_dict[view]['ax'].text(map_view_dict[view]['atlas'].shape[0]//2 + 2, 0, 'A',fontsize=15,fontweight='bold')
                    map_view_dict[view]['ax'].text(map_view_dict[view]['atlas'].shape[0]-10,map_view_dict[view]['atlas'].shape[1]//2+2,'R',fontsize=15,fontweight='bold')
                    map_view_dict[view]['ax'].text(map_view_dict[view]['atlas'].shape[0]//2,map_view_dict[view]['atlas'].shape[1]-5,'P',fontsize=15,fontweight='bold')
                elif view == 'coronal':
                    map_view_dict[view]['ax'].text(0,map_view_dict[view]['atlas'].shape[1]//2 + 2, 'L',fontsize=15,fontweight='bold')
                    map_view_dict[view]['ax'].text(map_view_dict[view]['atlas'].shape[0]//2 + 2, 0, 'S',fontsize=15,fontweight='bold')
                    map_view_dict[view]['ax'].text(map_view_dict[view]['atlas'].shape[0]-10,map_view_dict[view]['atlas'].shape[1]//2+2,'R',fontsize=15,fontweight='bold')
                    map_view_dict[view]['ax'].text(map_view_dict[view]['atlas'].shape[0]//2,map_view_dict[view]['atlas'].shape[1],'I',fontsize=15,fontweight='bold')
                elif view == 'sagittal':
                    map_view_dict[view]['ax'].text(0,map_view_dict[view]['atlas'].shape[1]//2 + 2, 'P',fontsize=15,fontweight='bold')
                    map_view_dict[view]['ax'].text(map_view_dict[view]['atlas'].shape[0]//2 + 2, 0, 'S',fontsize=15,fontweight='bold')
                    map_view_dict[view]['ax'].text(map_view_dict[view]['atlas'].shape[0]-10,map_view_dict[view]['atlas'].shape[1]//2+2,'A',fontsize=15,fontweight='bold')
                    map_view_dict[view]['ax'].text(map_view_dict[view]['atlas'].shape[0]//2,map_view_dict[view]['atlas'].shape[1]-10,'I',fontsize=15,fontweight='bold')
    
        if plot_focus:
            #atlas_slice=(x,y,z)
            s_x,s_y,s_z = atlas_slice
            plot_focus_kwargs={'ls':':','c':'y','alpha':1}
            for view,ax in map_view_dict.items():
                if view == 'axial':
                    map_view_dict[view]['ax'].axhline(y-s_y+padding_y//2,xmin=.1,xmax=.9,**plot_focus_kwargs)
                    map_view_dict[view]['ax'].axvline(s_x+padding_x//2,ymin=.1,ymax=.9,**plot_focus_kwargs)
                elif view == 'coronal':
                    map_view_dict[view]['ax'].axhline(z-s_z+padding_z//2,xmin=.1,xmax=.9,**plot_focus_kwargs)
                    map_view_dict[view]['ax'].axvline(s_x+padding_x//2,ymin=.1,ymax=.9,**plot_focus_kwargs)
                elif view == 'sagittal':
                    map_view_dict[view]['ax'].axhline(z-s_z+padding_z//2,xmin=.1,xmax=.9,**plot_focus_kwargs)
                    map_view_dict[view]['ax'].axvline(s_y+padding_y//2,ymin=.1,ymax=.9,**plot_focus_kwargs)
            
        return fig, map_view_dict
        
    
    @classmethod
    def get_ROIs_coordinates(cls,
                             atlas_file:Union[str,nib.nifti1.Nifti1Image])->pd.DataFrame:
        """
        Get ROIs voxel indices and scanner coordinate.
        Parameters
        ----------
        atlas_file : Union[str,nib.nifti1.Nifti1Image]
            pathway to nifti file or the nib.load nifti file.
        Returns
        -------
        ROIs_coord : pd.DataFrame
            dictionary where for the key is label, and value is the x,y,z coordinates.
        """
        brain_map = Brainmap(atlas_file)
        brain_map.atlas[np.isnan(brain_map.atlas)] = 0 # if nan exist set to 0
        transform_matrix = brain_map.atlas_file.affine[:-1,:]
        ROIs_coord = defaultdict(list)
        for label in np.unique(brain_map.atlas):
            if label != 0:
                ROIs_coord[label] = [coord.mean() for coord in np.where(brain_map.atlas == label)]
                ROIs_coord[label].extend(list(np.matmul(transform_matrix,np.array(ROIs_coord[label] + [1]))))
        ROIs_coord = pd.DataFrame(ROIs_coord).T
        ROIs_coord.reset_index(inplace=True)
        ROIs_coord.columns = ['Label','X_vox','Y_vox','Z_vox','X_sca','Y_sca','Z_sca']
        return ROIs_coord

        
class Geneset:

    @staticmethod
    def create_heatmap(gene_set_table:pd.DataFrame,
                       genes_set_column:str = 'GeneSet',
                       genes_list_column:str = 'genes',
                       gene_table:pd.DataFrame = None,
                       top:int = 20,
                       ordered_by:str=None,
                       gene_table_gene_name:str='Genes_Name') -> List[np.array]:
        """
        Create a heatmap of gene set analysis, where the x-axis is the list of genes, and y-axis is the gene set list.
        Args:
            gene_set_table (pd.DataFrame): enrichment result in table format
            |Geneset|P-value for phenotype 1| P-value for phenotype 2|List of genes| etc. (this is the FUMA table result)
            genes_set_column (str, optional): the gene set column name. Defaults to 'GeneSet'.
            genes_list_column (str, optional): the gene list column name. Defaults to 'genes'.
            gene_table (pd.DataFrame, optional): table containing rows of genes (or SNPs) and columns of P-value associated with 1 or 2 phenotypes (usually 1 for variable of interest and 1 taken directly from GWAS schizophrenia). Defaults to None.
        Note:
        The following genes name in the FUMA Gene-sets do not correspond with genes name in gene-table
        ['ADGRV1' if gene == 'GPR98' else 'ADGRB3' if gene == 'BAI3' else gene for gene in FUMA_gene_sets]
        
        Returns:
            heatmap: binary np.array, the x axis = list of genes, y axis = gene sets, 1 where there is a presence of the gene in gene set.
            all_genes = genes names on the x-axis
            gene_sets = genes set names on the y-axis
        """
        def heatmap_array(genesets:List[str],
                          genelist:List[str],
                          geneset_dict:dict) -> np.array:
            """
            Attributes:
                genesets = list of gene sets
                genelist = list of genes
                geneset_dict = dictionary where keys are genesets, and values are gene lists
            Return
                heatmap: binary np.array, the x axis = list of genes, y axis = gene sets, 1 where there is a presence of the gene in gene set.
                all_genes = genes names on the x-axis
                gene_sets = genes set names on the y-axis
            """
            heatmap = np.zeros((len(genesets),len(genelist)))
            for row,gene_set in enumerate(genesets):
                for column, gene in enumerate(genelist):
                    if gene in geneset_dict[gene_set]:
                        heatmap[row,column] = 1
            # new_idx = [idx for idx,gene in enumerate(genelist) if gene in list(geneset_dict.values())[0]]
            # old_idx = [idx for idx in range(len(genelist)) if idx not in new_idx]
            # new_idx = new_idx + old_idx
            # heatmap = heatmap[:,new_idx]
            # genelist = [genelist[idx] for idx in new_idx]
            return heatmap, genelist, list(geneset_dict.keys())
        
        gene_set_dict = {k:v.split(':') for k,v in zip(gene_set_table[genes_set_column].tolist(),gene_set_table[genes_list_column].tolist())}
        all_genes = [gene for gene_set in gene_set_dict.values() for gene in gene_set] #all of the genes found in the enrichment result table
        all_genes = list(set(all_genes)) # get the unique values
        all_genes_sets = gene_set_dict.keys()
        if top is not None:
            if ordered_by is not None:
                if gene_table is None:
                    raise ValueError('Must provide gene table')
                gene_table.replace('ADGRV1','GPR98',inplace=True)
                gene_table.replace('ADGRB3','BAI3',inplace = True)
        
                gene_table_considered = gene_table[gene_table[gene_table_gene_name].isin(all_genes)].sort_values(by=ordered_by)
                
                gene_table_considered = gene_table_considered.drop_duplicates(gene_table_gene_name,keep='first') # if there is a duplicate in the gene name keep the first (lowest p-value).
            
                gene_list_considered = gene_table_considered[gene_table_gene_name].tolist()[:top] # the gene_list_to_considered
                
                return heatmap_array(all_genes_sets,
                                     gene_list_considered,
                                     gene_set_dict)
            else:
                heatmap,gene_list_considered, gene_sets = heatmap_array(all_genes_sets,
                                        all_genes,
                                        gene_set_dict)
                heatmap = heatmap[:,:top]
                gene_list_considered = gene_list_considered[:top]
                return heatmap, gene_list_considered, gene_sets
        else:
            return heatmap_array(all_genes_sets,
                                 all_genes,
                                 gene_set_dict)
    
    @staticmethod
    def visualise_enrichment_p_value(gene_set_table:pd.DataFrame,
                                     x:str='adjP',
                                     y:str = 'GeneSet',
                                     colour_by:str = 'Proportion',
                                     xlabel:str = None,
                                     ylabel:str = None,
                                     ax:np.array=None):
        """Visualise the enrichment p-value from the gene-set table

        Args:
            gene_set_table (pd.DataFrame): the gene set table. (FUMA table output)
            x (str, optional): to be plotted on the x axis. Defaults to 'adjP'.
            y (str, optional): to be plotted on the y axis. Defaults to 'GeneSet'.
            colour_by (str, optional): color the bar. Defaults to 'Proportion'.
            xlabel (str, optional): x label. Defaults to None.
            ylabel (str, optional): y label. Defaults to None.
            ax (np.array, optional): _description_. Defaults to None.

        Returns:
            plt.plot
        """
        norm = plt.Normalize(gene_set_table[colour_by].min(),
                             gene_set_table[colour_by].max())
        sm = plt.cm.ScalarMappable(cmap='Reds',norm = norm)
        sm.set_array([])
        
        g = sns.barplot(x=-np.log10(gene_set_table[x]), y=y, color=colour_by, data=gene_set_table,palette='Reds', 
                        dodge=False,ax=ax)
        ax.set_ylabel(ylabel)
        ax.set_xlabel(xlabel)
        # ax.legend_.remove()
        cbar = ax.figure.colorbar(sm,ax = ax)
        cbar.set_label(colour_by,fontsize=15)
        ax.set_yticks([])        
        return ax
    
    @staticmethod    
    def visualise_heatmap(heatmap:np.array,
                          all_genes:List[str],
                          gene_sets:List[str],
                          ax:np.array,**figkwargs)->None:
        """Visualise the gene-set heatmap

        Args:
            heatmap (np.array): the heatmap generated by GeneSet.create_heatmap
            all_genes (List[str]): the list of genes generated by GeneSet.create_heatmap
            ax (np.array): the plt.Ax to plot on.
        """
        aspect=figkwargs.get('aspect','equal')
        x_tickrotation=figkwargs.get('x_tickrotation',45)
        y_tickrotation=figkwargs.get('y_tickrotation',45)
        x_tickfontsize=figkwargs.get('x_tickfontsize',15)
        y_tickfontsize=figkwargs.get('y_tickfontsize',15)
        ax.imshow(heatmap,vmin=0, vmax=1,aspect=aspect,cmap='Blues')
        ax.set_xticks(np.arange(0,len(all_genes),1))
        ax.set_yticks(np.arange(0,len(gene_sets),1))
        
        ax.set_xticks(np.arange(-.5, len(all_genes), 1), minor=True)
        ax.set_yticks(np.arange(-.5, len(gene_sets), 1), minor=True)
        
        ax.set_xticklabels(all_genes,rotation=x_tickrotation,fontsize=x_tickfontsize)
        ax.set_yticklabels(gene_sets,rotation=y_tickrotation,fontsize=y_tickfontsize)
        ax.grid(which='minor', color='w', linestyle='-', linewidth=2)
        return ax
    
    @staticmethod
    def visualise_gene_p_value(gene_table:pd.DataFrame,
                               all_genes:List[str],
                               gene_table_gene_name:str='Genes_Name',
                               ordered_by:str=None,
                               coloured_by:str=None,
                               bar_number:str='N_SNP',
                               p_threshold:float=5e-08,
                               ax:np.array=None,
                               cbar_ax=None,**kwargs)->None:
        """Visualise the p-value of the genes in genes list.

        Args:
            gene_table (pd.DataFrame): _description_
            all_genes (List[str]): _description_
            ordered_by (str,optional): the p-value column name to order by
            coloured_by (str, optional): the p-value column name to colour the bar. Defaults to P_schizo.
            bar_number (str, optional): the column name of number of SNPs in the gene. Defaults to N_SNPs.
            p_threshold (float, optional): _description_. Defaults to None.
            ax: the plt.Axes
        """
        gene_table = gene_table[gene_table[gene_table_gene_name].isin(all_genes)]
        gene_table = gene_table.sort_values(by=ordered_by).drop_duplicates(gene_table_gene_name,keep='first')# order and drop the duplicates
        gene_table[gene_table_gene_name] = pd.Categorical(gene_table[gene_table_gene_name],
                                                          categories=all_genes,
                                                          ordered=True)
        gene_table = gene_table.sort_values(by=gene_table_gene_name).reset_index(drop=True)
        bar_plot_y_axis = -np.log10(gene_table[ordered_by].tolist())
        
        g = sns.barplot(x=gene_table_gene_name,
                        y=bar_plot_y_axis,
                        data=gene_table,
                        ax=ax)
        cbar_label=kwargs.get('cbar_label','disease')
        ylabel=kwargs.get('ylabel','phenotype')
        if coloured_by is not None:
            bar_plot_colour_by = -np.log10(gene_table[coloured_by].tolist())
            if p_threshold is not None:
                bar_clrs = ['grey' if x < -np.log10(p_threshold) else 'red' for x in bar_plot_colour_by]
                for patch,bar_clr in zip(g.patches,bar_clrs):
                    patch.set_color(bar_clr)
                    
            else:
                pal = sns.color_palette('coolwarm',len(bar_plot_colour_by))
                rank = bar_plot_colour_by.argsort().argsort()
                index = gene_table.index.values
                my_cmap = ListedColormap(pal)
                norm = plt.Normalize(0, bar_plot_colour_by.max())
                sm = plt.cm.ScalarMappable(cmap=my_cmap,norm=norm)
                sm.set_array([])
                palette = np.array(pal)
                for patch,bar_clr in zip(g.patches,palette[rank[index]]):
                    patch.set_color(bar_clr)
                if cbar_ax is not None:
                    cbar = g.figure.colorbar(sm,cax = cbar_ax)
                    if cbar_label is not None:
                        cbar.set_label('$-log_{10}(SNP p-value)%s$'%cbar_label,fontsize=15)

        if bar_number is not None:                   
            for patch,label in zip(g.patches,gene_table.loc[:,bar_number].tolist()):
                if label > 1:
                    ax.annotate(label,
                                (patch.get_x()*1.005,
                                patch.get_height()*1.005),fontsize = 15)
        
        ax.set_xticks([])
        ax.set_xlabel('') 
        
        ax.set_ylabel('$-log_{10}(SNP p-value) %s$'%ylabel,fontsize=15)
        return ax
        
        
        
        
    
def visualise_heatmap(df,
                      ax,
                      xlabel:str=None,
                      ylabel:str=None,
                      rotation=0):
    
    heatmap = df.copy()
    g = ax.imshow(heatmap,cmap='jet')
    ax.set_xticks(np.arange(0,heatmap.shape[1],1))
    ax.set_yticks(np.arange(0,heatmap.shape[0],1))
    
    ax.set_xticks(np.arange(-.5, heatmap.shape[1], 1), minor=True)
    ax.set_yticks(np.arange(-.5, heatmap.shape[0], 1), minor=True)
    
    ax.set_xticklabels(xlabel,rotation=rotation,fontsize=12)
    ax.set_yticklabels(ylabel,rotation=rotation,fontsize=12)
    ax.grid(which='minor', color='w', linestyle='-', linewidth=2)
    
    return g
    
    
    
        
    
    

    








        
        
