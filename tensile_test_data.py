# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 17:31:29 2020

@author: aso
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os
from tqdm import tqdm
from copy import deepcopy

from pyRegression.linear_regression import lin_reg_all_sections
from pyPreprocessing.smoothing import smoothing
from little_helpers.num_derive import derivative


class tensile_test():
    def __init__(self, import_file, import_mode, unit_strain='%',
                 unit_stress='kPa', **kwargs):
        """
        Initialize data container for tensile test data.
        
        Original raw data are stored in self.raw_original. The data is then
        streamlined and stored in self.raw.

        Parameters
        ----------
        import_file : string
            The file path of the file that contains the tensile test data. The
            data will be imported to self.raw_original. The file will usually
            be an Excel file, but could also be an ASCII file. The
            corresponding import filters have to be defined in
            self.import_data.
        import_mode : string
            Selects the import filter used when importing the data. Currently
            allowed values are 'Marc_Stuhlmüller', 'Philipp Manglkammer' and
            'Lena_Schunter'.
        unit_strain : string, optional
            The unit of the strain values in the dataset. Allowed values are
            '', meaning that it is dimensionless, and '%', meaning that the
            strain is given in %. The default is '%'.
        unit_stress : string, optional
            The unit of the stress values in the dataset. The default is 'kPa'.
        **kwargs : 
            preload : float
                If given, all stress values smaller than preload will be
                dropped from the dataset. The corresponding tool distance will
                be defined as zero strain and the strain values are
                recalculated accordingly. Thus, it only works when a column
                exists within the dataset that contains the tool distance
                during the tensile test.

        Raises
        ------
        ValueError
            If no valid unit_strain is given.

        Returns
        -------
        None.

        """

        # strain units can be '%' or '' 
        self.unit_strain = unit_strain
        self.unit_stress = unit_stress
        self.preload = kwargs.get('preload', None)

        if self.unit_strain == '':
            self.strain_conversion_factor = 1
        elif self.unit_strain == '%':
            self.strain_conversion_factor = 100
        else:
            raise ValueError('No valid unit_strain. Allowed values are \'%\' or \'\'.')

        self.e_modulus_title = 'e_modulus [' + self.unit_stress + ']'
        self.linear_limit_title = 'linear_limit [' + self.unit_strain + ']'
        self.strength_title = 'strength [' + self.unit_stress + ']'
        self.toughness_title = 'toughness [' + self.unit_stress + '] (Pa = J/m^3)'
        self.elongation_at_break_title = 'elongation_at_break [' + self.unit_strain + ']'
        self.slope_limit_title = 'slope_limit [' + self.unit_stress + '/' + self.unit_strain + ']'
        self.intercept_limit_title = 'intercept_limit [' + self.unit_stress + ']'

        self.results = pd.DataFrame([], columns=[
                'name', self.e_modulus_title, self.linear_limit_title,
                self.strength_title, self.toughness_title,
                self.elongation_at_break_title, self.slope_limit_title,
                self.intercept_limit_title])

        self.import_file = import_file
        self.import_mode = import_mode
        self.import_data()
        # copy original raw data and use this copy for further processing
        self.raw = deepcopy(self.raw_original)
        for sample in self.raw:
            sample = self.streamline_data(sample)

    def import_data(self):
        """
        Import the data from the external sources into self.raw_original.

        Multiple datasets may be present in the source file given.
        self.raw_original is a list of DataFrames. Each dataframe contains the
        data of one tensile test. If only one dataset is present, it is a list
        containing only one DataFrame.

        Returns
        -------
        None.

        """
        if self.import_mode == 'Marc_Stuhlmueller':
            try:
                # Read excel file
                raw_excel = pd.ExcelFile(self.import_file)
                # Save sheets starting with the third into list
                self.raw_original = []
                self.results['name'] = raw_excel.sheet_names[3:]
                for sheet_name in raw_excel.sheet_names[3:]:
                    self.raw_original.append(
                            raw_excel.parse(sheet_name, header=2,
                                            names=['strain', 'Standardkraft',
                                                   'stress']))
            except Exception as e:
                print('Error while file import in line ' +
                      str(sys.exc_info()[2].tb_lineno) + ': ', e)

        elif self.import_mode == 'Philipp Manglkammer':
            #try:
            # Read excel file
            raw_excel = pd.ExcelFile(self.import_file)
            # Save sheets starting with the third into list
            self.raw_original = []
            self.results['name'] = raw_excel.sheet_names[3:]
            for sheet_name in raw_excel.sheet_names[3:]:
                self.raw_original.append(
                        raw_excel.parse(sheet_name, header=2,
                                        names=['stress', 'strain'],
                                        usecols=[0, 1]))
            #except Exception as e:
            #    print('Error while file import in line ' +
            #          str(sys.exc_info()[2].tb_lineno) + ': ', e)

        elif self.import_mode == 'Lena_Schunter':
            # Read excel file
            raw_excel = pd.ExcelFile(self.import_file)
            # Save sheets starting with the second into list
            self.raw_original = []
            self.results['name'] = raw_excel.sheet_names[2:]
            for sheet_name in raw_excel.sheet_names[2:]:
                self.raw_original.append(
                        raw_excel.parse(sheet_name, header=2,
                                        names=['tool_distance', 'strain',
                                               'stress'],
                                        usecols=[0, 1, 2]))

        else:
            raise ValueError('No valid import mode entered.')

    def streamline_data(self, sample):
        """
        Streamline a dataset to make it fit for further analysis.
        
        Typical problems with real datasets are duplicate values, unsorted
        strain values (especially at the test start) and NaN values due to
        missing values in the source file. Additionally, the data is cropped
        if wanted based on certain criteria (currently only defined by
        self.preload).

        Parameters
        ----------
        sample : DataFrame
            A dataset containing the stress-strain data of a single sample.

        Returns
        -------
        sample : DataFrame
            The streamlined dataset.

        """
        sample.drop_duplicates('strain', keep='first', inplace=True)
        sample.sort_values(by=['strain'], inplace=True)
        if self.preload is not None:
            sample.where(sample['stress'] >= self.preload, inplace=True)
            sample.dropna(inplace=True)
            h_0 = sample['tool_distance'].iloc[0]
            sample['strain'] = (h_0-sample['tool_distance'])/h_0 * self.strain_conversion_factor
            sample['deriv'] = derivative(sample['strain'].values,
                                         sample[['stress']].values.T).T
        else:
            sample.dropna(inplace=True)

        return sample

    def smooth_data(self, sample, window, poly_order, data_points=None):
        """
        Smoothes a dataset to allow a cleaner analysis of the slopes.

        Parameters
        ----------
        sample : DataFrame
            A dataset containing the stress-strain data of a single sample.
        window : int, optional
            The number of datapoints used around a specific datapoint for the
            Savitzky Golay method. Default is 500.
        polyorder : int, optional
            The polynomial order used for the Savitzky Golay method. Default is
            2.
        data_points : int. optional
            The number of datapoints used for interpolation of the dataset to
            an evenly spaced dataset. This is a prerequisite for the Savitzky
            Golay method and is therefore always done here.Default is one order
            of magnitude more than datapoints in the dataset.

        Returns
        -------
        sample : TYPE
            DESCRIPTION.

        """
        smoothed_sample = sample.loc[:, 'stress'].values
        x_coordinate = sample.loc[:, 'strain'].values
        
        if data_points is None:
            data_points = int(10**np.ceil(np.log10(len(x_coordinate))))

        strain_interpolated, smoothed_sample = smoothing(
            smoothed_sample[np.newaxis], 'sav_gol', interpolate=True,
            point_mirror=True, x_coordinate=x_coordinate,
            savgol_points=window, poly_order=poly_order,
            data_points=data_points)

        sample = pd.DataFrame(
                list(zip(strain_interpolated, np.squeeze(smoothed_sample.T))),
                columns=['strain', 'stress'])

        return sample

    def calc_e_modulus(self, r_squared_lower_limit=0.995, lower_strain_limit=0,
                       upper_strain_limit=50, smoothing=True, **kwargs):
        """
        Calculate the E modulus from the tensile test data.

        The fitting algorithm works in such a way that it starts a linear
        regression with the first two datapoints from which the slope and the
        coefficient of determination (R^2) is obtained. This procedure is
        repeated, adding one datapoint for each iteration, until
        upper_strain_limit is reached. The E modulus is then determined by the
        point where R^2 is still greater than r_squared_lower_limit.

        Parameters
        ----------
        r_squared_lower_limit : float, optional
            The R^2 limit. Defines the value of R^2 that is still acceptable
            for the fit to be considered linear. The default is 0.995.
        lower_strain_limit : float, optional
            The lower strain limit used for the fit. The default is 0.
        upper_strain_limit : float, optional
            The upper strain limit used for the fit. It might make sense to
            give a reasonably low limit if computation speed is important. The
            number of linear fit that have to be performed for each dataset is
            equal to the number of datapoints between lower_strain_limit and
            upper_strain_limit. The default is 50.
        smoothing : boolean, optional
            Defines if the dataset is smoothed before the calculations. Usually
            this is necessary. Smoothing is controlled by kwargs explained
            below, a Savitzky Golay method is used. The default is True. 
        **kwargs : 
            sav_gol_window : int, optional
                The number of datapoints used around a specific datapoint for
                the Savitzky Golay method. Default is 500.
            sav_gol_polyorder : int, optional
                The polynomial order used for the Savitzky Golay method.
                Default is 2.
            data_points : int. optional
                The number of datapoints used for interpolation of the dataset
                to an evenly spaced dataset. This is a prerequisite for the
                Savitzky Golay method and is therefore always done here.Default
                is one order of magnitude more than datapoints in the dataset.

        Returns
        -------
        DataFrame
            The current results DataFrame.

        """

        e_modulus = []
        slope_limit = []
        intercept_limit = []
        linear_limit = []
        self.r_squared_lower_limit = r_squared_lower_limit

        # Data pre-processing for E modulus calculation
        self.raw_processed = []
        for sample in self.raw:
            if smoothing:
                sav_gol_window = kwargs.get('sav_gol_window', 500)
                sav_gol_polyorder = kwargs.get('sav_gol_polyorder', 2)
                sample = self.smooth_data(sample, sav_gol_window,
                                          sav_gol_polyorder,
                                          data_points=kwargs.get(
                                              'data_points', None))
            self.raw_processed.append(sample)

        self.raw_processed_cropped = []
        # max_strain_cropped = 0
        for sample in tqdm(self.raw_processed):
            sample_cropped = sample.copy()
            # Extract relevant strain range for youngs modulus
            indexNames = sample_cropped[(
                sample_cropped['strain'] <= lower_strain_limit)].index
            indexNames_2 = sample_cropped[(
                sample_cropped['strain'] >= upper_strain_limit)].index
            sample_cropped.drop(indexNames, inplace=True)
            sample_cropped.drop(indexNames_2, inplace=True)
            sample_cropped.reset_index(drop=True, inplace=True)

            # do regression and append results to sample DataFrame
            regression_results, curr_linear_limit, curr_linear_limit_stress, curr_slope_at_limit, curr_intercept_at_limit = lin_reg_all_sections(sample_cropped.loc[:, 'strain'].values, sample_cropped.loc[:, 'stress'].values, r_squared_limit = r_squared_lower_limit, mode = 'both')
            sample_cropped = pd.concat([sample_cropped, regression_results],
                                       axis=1)

            slope_limit.append(curr_slope_at_limit)
            intercept_limit.append(curr_intercept_at_limit)
            linear_limit.append(curr_linear_limit)

            # Calculate youngs modulus
            curr_e_modulus = (np.around(curr_slope_at_limit, decimals=3)*
                              self.strain_conversion_factor)

            # Save result in list
            e_modulus.append(curr_e_modulus.round(3))
            self.raw_processed_cropped.append(sample_cropped)

        self.results[self.e_modulus_title] = e_modulus
        self.results[self.linear_limit_title] = linear_limit
        self.results[self.slope_limit_title] = slope_limit
        self.results[self.intercept_limit_title] = intercept_limit
        return self.results

    def calc_strength(self):
        """
        Calculate the sample strengths.

        Calculation is done simply by selecting the maximum stress observed in
        the datasets.

        Returns
        -------
        list
            A list containing the calculation results.

        """
        self.strength = []
        for sample in self.raw:
            self.strength.append(
                    np.around(sample['stress'].max(), decimals=1))
            
        self.results[self.strength_title] = self.strength
        return self.strength

    def calc_toughness(self):
        """
        Calculate the sample toughnesses.

        Calculation is done by integrating over the stress-strain curves.

        Returns
        -------
        list
            A list containing the calculation results.

        """
        self.toughness = []
        for sample in self.raw:
            self.toughness.append(
                    np.around(np.trapz(sample['stress'],
                                       x=sample['strain'])/
                self.strain_conversion_factor, decimals=1))
        self.results[self.toughness_title] = self.toughness
        return self.toughness

    def calc_elongation_at_break(self):
        """
        Calculate the elongation at break of the samples.

        Calculation is done simply by selecting the maximum strain observed in
        the datasets.

        Returns
        -------
        list
            A list containing the calculation results.

        """
        self.elongation_at_break = []
        for sample in self.raw:
            self.elongation_at_break.append(
                    np.around(sample['strain'].at[sample[
                            'stress'].idxmax()],
                decimals=1))
        self.results[self.elongation_at_break_title] = self.elongation_at_break
        return self.elongation_at_break

    def generate_plots(self, export_path=None, **kwargs):
        if (self.results[self.e_modulus_title].isna().values.any()
        ) or (self.results[self.linear_limit_title].isna().values.any()):
            r_squared_lower_limit = kwargs.get('r_squared_lower_limit', 0.995)
            lower_strain_limit = kwargs.get('lower_strain_limit', 0)
            upper_strain_limit=kwargs.get('upper_strain_limit', 15)
            smoothing = kwargs.get('smoothing', True)
            sav_gol_window = kwargs.get('sav_gol_window', 500)
            sav_gol_polyorder = kwargs.get('sav_gol_polyorder', 2)
            data_points=kwargs.get('data_points', 10000)

            self.calc_e_modulus(r_squared_lower_limit=r_squared_lower_limit,
                                lower_strain_limit=lower_strain_limit,
                                upper_strain_limit=upper_strain_limit,
                                smoothing=smoothing,
                                sav_gol_window=sav_gol_window,
                                sav_gol_polyorder=sav_gol_polyorder,
                                data_points=data_points)
            
        if self.results[self.strength_title].isna().values.any():
            self.calc_strength()
        if self.results[self.toughness_title].isna().values.any():
            self.calc_toughness()
        if self.results[self.elongation_at_break_title].isna().values.any():
            self.calc_elongation_at_break()
        
        global_min_stress = 0
        global_max_stress = 0
        global_min_strain = 0
        global_max_strain = 0
        
        for sample in self.raw:
            if sample['stress'].max() > global_max_stress:
                global_max_stress = sample['stress'].max()
            if sample['strain'].max() > global_max_strain:
                global_max_strain = sample['strain'].max()
            if sample['stress'].min() < global_min_stress:
                global_min_stress = sample['stress'].min()
            if sample['strain'].min() < global_min_strain:
                global_min_strain = sample['strain'].min()
                
        max_strain_cropped = 0
        for sample in self.raw_processed_cropped:
            if sample['strain'].iloc[-1] > max_strain_cropped:
                max_strain_cropped = sample['strain'].iloc[-1]
                
        # Plot whole graph with regression line
        for ii, (raw_sample, processed_sample, el_at_break, strength,
                curr_linear_limit, curr_slope_limit, curr_intercept_limit
                ) in enumerate(zip(self.raw, self.raw_processed, self.elongation_at_break,
                self.strength, self.results[self.linear_limit_title], self.results[self.slope_limit_title], self.results[self.intercept_limit_title])):
            fig = plt.subplot(len(self.raw), 3, 1+ii*3)
            if ii==0: plt.title('Tensile test')
            if ii==int(len(self.raw)/2): plt.ylabel(r'$\sigma$ [kPa]')
            if ii==len(self.raw)-1: 
                plt.xlabel(r'$\epsilon$ [%]')
            else:
                fig.axes.xaxis.set_ticklabels([])
            plt.axvline(el_at_break,ls='--',c='k',lw=0.5)
            plt.axhline(strength,ls='--',c='k',lw=0.5)
            plt.plot(raw_sample['strain'],raw_sample['stress'], linestyle='-')
            plt.plot(processed_sample['strain'],processed_sample['stress'], linestyle='-',color='y')
            plt.plot(np.linspace(0,curr_linear_limit),curr_slope_limit*np.linspace(0,curr_linear_limit)+curr_intercept_limit, color='indianred')
            plt.xlim(global_min_strain,1.05*global_max_strain)
            plt.ylim(global_min_stress,1.05*global_max_stress)

        # Plot r-sqaured 
        plt.subplots_adjust(wspace = 0.5)
        for ii,(emod_sample,curr_linear_limit) in enumerate(
                zip(self.raw_processed_cropped,
                    self.results[self.linear_limit_title])):
            fig = plt.subplot(len(self.raw), 3, 2+ii*3)
            if ii==0: plt.title('Coefficient of determination')
            if ii==int(len(self.raw)/2): plt.ylabel('$R^2$')
            if ii==len(self.raw)-1: 
                plt.xlabel(r'$\epsilon$ [%]')
            else:
                fig.axes.xaxis.set_ticklabels([])
            plt.yticks([0.975,1.0])
            plt.plot(emod_sample.loc[1:,'strain'],emod_sample.loc[1:,'r_squared'], color='indianred')
            plt.axvline(curr_linear_limit,ls='--',c='k',lw=0.5)
            plt.axhline(self.r_squared_lower_limit,ls='--',c='k',lw=0.5)
            plt.xlim(0,max_strain_cropped)
            plt.ylim(0.95, 1)
            
        # Plot E modulus
        for ii,(emod_sample,curr_linear_limit) in enumerate(
                zip(self.raw_processed_cropped,
                    self.results[self.linear_limit_title])):
            fig = plt.subplot(len(self.raw), 3, 3+ii*3)
            if ii==0: plt.title('E modulus')
            if ii==int(len(self.raw)/2): plt.ylabel('$E$ [kPa]')
            if ii==len(self.raw)-1: 
                plt.xlabel(r'$\epsilon$ [%]')
            else:
                fig.axes.xaxis.set_ticklabels([])
            #plt.ylim(0.95, 1)
            #plt.yticks([0.975,1.0])
            plt.plot(emod_sample.loc[1:,'strain'],emod_sample.loc[1:,'slopes']*100, color='indianred')
            plt.axvline(curr_linear_limit,ls='--',c='k',lw=0.5)
            plt.xlim(0,max_strain_cropped)

        if export_path is not None:
            export_name = kwargs.get('export_name', 'Tensile test')
            # Save figure as svg
            if not os.path.exists(export_path + 'Plots/'):
                os.makedirs(export_path + 'Plots/')
            plt.savefig(export_path + 'Plots/' + export_name + '.png', dpi=500)
            #plt.clf()
            plt.close()


if __name__ == "__main__":
    #file = r'Z:\Charakterisierungen und Messungen\Python\zz_not_yet_in_git\04_Zugversuch-Auswertung\62\62.xls'
    #file = r'Z:/Lehre/Studentische Arbeiten/02 Abgeschlossene Arbeiten/2019_Marc Stuhlmüller/Messdaten Zugversuche/03_Messdaten Zugversuche bis 15/23.xls'
    # file = r'Z:\Charakterisierungen und Messungen\Python\zz_not_yet_in_git\04_Zugversuch-Auswertung\62\Mappe1.xlsx'
    # file = r'/home/almami/Alexander/Python_Skripte/yy_Not_yet_in_git/04_Zugversuch-Auswertung/62/62.xls'

    file = r'Z:\Lehre\Studentische Arbeiten\02 Abgeschlossene Arbeiten\2020_Rebecca Hirsch\Messdaten_Zugversuche.xls'

    tensile_test = tensile_test(file, 'Marc_Stuhlmueller', unit_strain='%',
                                unit_stress='MPa')
    tensile_test.calc_e_modulus(r_squared_lower_limit = 0.998, upper_strain_limit=5,
                            sav_gol_window=500, data_points=10000)
    tensile_test.calc_strength()
    tensile_test.calc_toughness()
    tensile_test.calc_elongation_at_break()
    test_results = tensile_test.results
