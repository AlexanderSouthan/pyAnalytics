# -*- coding: utf-8 -*-
"""
For inspection of confocal LSM datasets. 
"""

import numpy as np
from tqdm import tqdm
import glob
import imageio
import skimage.io

class lsm_data:
    def __init__(self,directory,file_extension,xInterval,yInterval,zInterval,generate_projections=True,image_export_path=None,export_name=None):
        self.directory = directory
        self.file_extension = file_extension
        self.image_export_path = image_export_path
        self.export_name = export_name
        self.xInterval = xInterval
        self.yInterval = yInterval
        self.zInterval = zInterval
        
        self.import_data()#imports images into self.intensities_multichrome
        self.multi2monochrome()#converts multichrome images to monochrome and stores them in self.intensities_monochrome        

        #the following six arrays are used for operations which select values from all data points
        #by fancy indexing, e.g. for maximum intensity projection or extraction of all zScans
        self.ind1_xy = np.tile(np.arange(np.shape(self.intensities_monochrome)[1]),(np.shape(self.intensities_monochrome)[2],1)).T
        self.ind2_xy = np.tile(np.arange(self.intensities_monochrome.shape[2]),(self.intensities_monochrome.shape[1],1))
        self.ind1_xz = np.tile(np.arange(np.shape(np.swapaxes(self.intensities_monochrome,0,1))[1]),(np.shape(np.swapaxes(self.intensities_monochrome,0,1))[2],1)).T
        self.ind2_xz = np.tile(np.arange(np.swapaxes(self.intensities_monochrome,0,1).shape[2]),(np.swapaxes(self.intensities_monochrome,0,1).shape[1],1))
        self.ind1_yz = np.tile(np.arange(np.shape(np.swapaxes(self.intensities_monochrome,0,2))[1]),(np.shape(np.swapaxes(self.intensities_monochrome,0,2))[2],1)).T
        self.ind2_yz = np.tile(np.arange(np.swapaxes(self.intensities_monochrome,0,2).shape[2]),(np.swapaxes(self.intensities_monochrome,0,2).shape[1],1))
        
        if generate_projections:
            self.generate_intensity_projections()#generates maximum, minimum and average intensity projections in 2D
            
            #the following lines generate maximum, minimum and average intensity projections in 1D
            self.zScanMax = np.amax(self.MaxIP_xzPlane_monochrome,axis=1)
            self.yScanMax = np.amax(self.MaxIP_xyPlane_monochrome,axis=1)
            self.xScanMax = np.amax(self.MaxIP_xzPlane_monochrome,axis=0)
            self.zScanMin = np.amin(self.MinIP_xzPlane_monochrome,axis=1)
            self.yScanMin = np.amin(self.MinIP_xyPlane_monochrome,axis=1)
            self.xScanMin = np.amin(self.MinIP_xzPlane_monochrome,axis=0)
            self.zScanAverage = np.mean(self.AvgIP_xzPlane_monochrome,axis=1)
            self.yScanAverage = np.mean(self.AvgIP_xyPlane_monochrome,axis=1)
            self.xScanAverage = np.mean(self.AvgIP_xzPlane_monochrome,axis=0)
        
    def import_data(self):
        self.file_list = glob.glob(self.directory + '*.' + self.file_extension)
        
        image_data = skimage.io.imread_collection(self.file_list)
        
        self.intensities_multichrome = np.zeros((len(self.file_list),np.shape(image_data[0])[0],np.shape(image_data[0])[1],np.shape(image_data[0])[2]),dtype='uint8')
        for ii,current_image in enumerate(tqdm(image_data)):
            self.intensities_multichrome[ii] = current_image   
            
        #the following three lines define the coordinate axes
        self.z_values = np.arange(0,self.zInterval*np.shape(self.intensities_multichrome)[0],self.zInterval)
        self.y_values = np.arange(0,self.yInterval*np.shape(self.intensities_multichrome)[1],self.yInterval)
        self.x_values = np.arange(0,self.xInterval*np.shape(self.intensities_multichrome)[2],self.xInterval)
            
    
    def multi2monochrome(self,mode = 'rgb_weighted',channel = None): #convert multichrome images to monochrome
        if mode == 'rgb_weighted':
            self.intensities_monochrome = np.round(np.average(self.intensities_multichrome,axis=3,weights=[0.2989,0.5870,0.1140])).astype(np.uint8)
        elif mode == 'channel':
            self.intensities_monochrome = self.intensities_multichrome[:,:,:,channel]
            
        return self.intensities_monochrome
    
    def average_xy_image_data(self,averaging_exponent = 4):
        #image_data_reduced = np.empty((len(image_data.file_list),IMAGE_PIXELS_PER_DIM//(2**AVERAGING_EXPONENT),IMAGE_PIXELS_PER_DIM//(2**AVERAGING_EXPONENT)))

        #image is averaged over averaging_number^2 pixels and stored in image_data_reduced
        averaging_number = 2**averaging_exponent
        remaining_pixels = self.intensities_monochrome.shape[1]//averaging_number
        
        image_data_reduced = np.mean(self.intensities_monochrome.reshape(len(self.file_list),-1,averaging_number),axis=2).reshape(len(self.file_list),self.intensities_monochrome.shape[1],remaining_pixels)
        image_data_reduced = np.mean(image_data_reduced.swapaxes(1,2).reshape(len(self.file_list),-1,averaging_number),axis=2).reshape(len(self.file_list),remaining_pixels,remaining_pixels)
        
        return image_data_reduced

        #for index,curr_image in enumerate(tqdm(image_data_monochrome)):
        #    curr_image = np.mean(curr_image.reshape(-1,averaging_number),axis=1).reshape(IMAGE_PIXELS_PER_DIM,remaining_pixels)
        #    curr_image = np.mean(curr_image.T.reshape(-1,averaging_number),axis=1).reshape(remaining_pixels,remaining_pixels).T
        #    image_data_reduced[index,:,:] = curr_image
        
    
    def generate_intensity_projections(self):
        """Generates maximum intensity projection from numpy array with 8-bit images. 
        Export is optional if export path and file name are given. """
        
        #extracts maximum values along first dimension
        index_for_MaxIP_z = np.argmax(self.intensities_monochrome,axis=0)#finds the index for maximum value in first dimension
        index_for_MaxIP_y = np.argmax(np.swapaxes(self.intensities_monochrome,0,1),axis=0)
        index_for_MaxIP_x = np.argmax(np.swapaxes(self.intensities_monochrome,0,2),axis=0)
        
        index_for_MinIP_z = np.argmin(self.intensities_monochrome,axis=0)#finds the index for minimum value in first dimension
        index_for_MinIP_y = np.argmin(np.swapaxes(self.intensities_monochrome,0,1),axis=0)
        index_for_MinIP_x = np.argmin(np.swapaxes(self.intensities_monochrome,0,2),axis=0)

        self.MinIP_xyPlane_multichrome = self.intensities_multichrome[index_for_MinIP_z,self.ind1_xy,self.ind2_xy]
        self.MinIP_xzPlane_multichrome = np.swapaxes(self.intensities_multichrome,0,1)[index_for_MinIP_y,self.ind1_xz,self.ind2_xz]
        self.MinIP_yzPlane_multichrome = np.swapaxes(self.intensities_multichrome,0,2)[index_for_MinIP_x,self.ind1_yz,self.ind2_yz]        
        self.MaxIP_xyPlane_multichrome = self.intensities_multichrome[index_for_MaxIP_z,self.ind1_xy,self.ind2_xy]
        self.MaxIP_xzPlane_multichrome = np.swapaxes(self.intensities_multichrome,0,1)[index_for_MaxIP_y,self.ind1_xz,self.ind2_xz]
        self.MaxIP_yzPlane_multichrome = np.swapaxes(self.intensities_multichrome,0,2)[index_for_MaxIP_x,self.ind1_yz,self.ind2_yz]
        self.AvgIP_xyPlane_multichrome = np.mean(self.intensities_multichrome,axis=0).astype(np.int64)
        self.AvgIP_xzPlane_multichrome = np.mean(np.swapaxes(self.intensities_multichrome,0,1),axis=0).astype(np.int64)
        self.AvgIP_yzPlane_multichrome = np.mean(np.swapaxes(self.intensities_multichrome,0,2),axis=0).astype(np.int64)
        
        self.MinIP_xyPlane_monochrome = self.intensities_monochrome[index_for_MinIP_z,self.ind1_xy,self.ind2_xy]
        self.MinIP_xzPlane_monochrome = np.swapaxes(self.intensities_monochrome,0,1)[index_for_MinIP_y,self.ind1_xz,self.ind2_xz]
        self.MinIP_yzPlane_monochrome = np.swapaxes(self.intensities_monochrome,0,2)[index_for_MinIP_x,self.ind1_yz,self.ind2_yz]
        self.MaxIP_xyPlane_monochrome = self.intensities_monochrome[index_for_MaxIP_z,self.ind1_xy,self.ind2_xy]
        self.MaxIP_xzPlane_monochrome = np.swapaxes(self.intensities_monochrome,0,1)[index_for_MaxIP_y,self.ind1_xz,self.ind2_xz]
        self.MaxIP_yzPlane_monochrome = np.swapaxes(self.intensities_monochrome,0,2)[index_for_MaxIP_x,self.ind1_yz,self.ind2_yz]
        self.AvgIP_xyPlane_monochrome = np.mean(self.intensities_monochrome,axis=0).astype(np.int64)
        self.AvgIP_xzPlane_monochrome = np.mean(np.swapaxes(self.intensities_monochrome,0,1),axis=0).astype(np.int64)
        self.AvgIP_yzPlane_monochrome = np.mean(np.swapaxes(self.intensities_monochrome,0,2),axis=0).astype(np.int64) 
    
        #if type(self.image_export_path) is not None and type(self.export_name) is not None:
        #    self.export_intensity_projections()
            
    
    def export_intensity_projections(self):
        imageio.imwrite(self.image_export_path + self.export_name + '_MinIP_xyPlane_multichrome.' + self.file_extension,self.MinIP_xyPlane_multichrome)
        imageio.imwrite(self.image_export_path + self.export_name + '_MinIP_xzPlane_multichrome.' + self.file_extension,self.MinIP_xzPlane_multichrome)
        imageio.imwrite(self.image_export_path + self.export_name + '_MinIP_yzPlane_multichrome.' + self.file_extension,self.MinIP_yzPlane_multichrome)
        imageio.imwrite(self.image_export_path + self.export_name + '_MaxIP_xyPlane_multichrome.' + self.file_extension,self.MaxIP_xyPlane_multichrome)
        imageio.imwrite(self.image_export_path + self.export_name + '_MaxIP_xzPlane_multichrome.' + self.file_extension,self.MaxIP_xzPlane_multichrome)
        imageio.imwrite(self.image_export_path + self.export_name + '_MaxIP_yzPlane_multichrome.' + self.file_extension,self.MaxIP_yzPlane_multichrome)
        imageio.imwrite(self.image_export_path + self.export_name + '_AvgIP_xyPlane_multichrome.' + self.file_extension,self.AvgIP_xyPlane_multichrome.astype(np.uint8))
        imageio.imwrite(self.image_export_path + self.export_name + '_AvgIP_xzPlane_multichrome.' + self.file_extension,self.AvgIP_xzPlane_multichrome.astype(np.uint8))
        imageio.imwrite(self.image_export_path + self.export_name + '_AvgIP_yzPlane_multichrome.' + self.file_extension,self.AvgIP_yzPlane_multichrome.astype(np.uint8))
            
        imageio.imwrite(self.image_export_path + self.export_name + '_MinIP_xyPlane_monochrome.tif',self.MinIP_xyPlane_monochrome)
        imageio.imwrite(self.image_export_path + self.export_name + '_MinIP_xzPlane_monochrome.tif',self.MinIP_xzPlane_monochrome)
        imageio.imwrite(self.image_export_path + self.export_name + '_MinIP_yzPlane_monochrome.tif',self.MinIP_yzPlane_monochrome)            
        imageio.imwrite(self.image_export_path + self.export_name + '_MaxIP_xyPlane_monochrome.tif',self.MaxIP_xyPlane_monochrome)
        imageio.imwrite(self.image_export_path + self.export_name + '_MaxIP_xzPlane_monochrome.tif',self.MaxIP_xzPlane_monochrome)
        imageio.imwrite(self.image_export_path + self.export_name + '_MaxIP_yzPlane_monochrome.tif',self.MaxIP_yzPlane_monochrome)
        imageio.imwrite(self.image_export_path + self.export_name + '_AvgIP_xyPlane_monochrome.tif',self.AvgIP_xyPlane_monochrome.astype(np.uint8))
        imageio.imwrite(self.image_export_path + self.export_name + '_AvgIP_xzPlane_monochrome.tif',self.AvgIP_xzPlane_monochrome.astype(np.uint8))
        imageio.imwrite(self.image_export_path + self.export_name + '_AvgIP_yzPlane_monochrome.tif',self.AvgIP_yzPlane_monochrome.astype(np.uint8))
    
    def xScan(self,yPos,zPos):
        return self.intensities_monochrome[zPos,yPos,:].T
    
    def yScan(self,xPos,zPos):
        return self.intensities_monochrome[zPos,:,xPos].T
    
    def zScan(self,xPos,yPos):
        return self.intensities_monochrome[:,yPos,xPos]
    
    def xz_slice(self,yPos):
        return np.squeeze(self.intensities_monochrome[:,yPos,:])
        
    def yz_slice(self,xPos):
        return np.squeeze(self.intensities_monochrome[:,:,xPos])
    
    def xy_slice(self,zPos):
        return np.squeeze(self.intensities_monochrome[zPos,:,:])