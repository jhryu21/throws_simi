clear;clc
[fname, pname] = uigetfile('*.txt','Choose a dat file to edit');
importname=[pname,'\' fname];
tdata=simiimport(importname);
tdata = tdata(1:end-2,:);
trialname = fname(1:end-4);

%time_r = round(tdata(:,1),2);
time = tdata(:,1);

px = tdata(:,2)*-1;
py = tdata(:,3);
pz = tdata(:,4);
vx = tdata(:,5)*-1;
vy = tdata(:,6);
vz = tdata(:,7);
vr = tdata(:,8);

[b,a] = butter(2,(10/(160/2)));
pxx = filtfilt(b,a,px);
pyy = filtfilt(b,a,py);
pzz = filtfilt(b,a,pz);

% pxx = px;
% pyy = py;
% pzz = pz;

%events_r =round(tdata(1:6,9),2);
eff = tdata(1:6,9);
ef = round(eff*160)+1;


% for i=1:1:6
%     ef(i,1) = find(time_r == events_r(i),1);
% end

speed_rel_r = vr(ef(6)-1);
speed_rel_z = vz(ef(6)-1);
speed_rel_y = vy(ef(6)-1);
rel_h = pz(ef(6)-1);

dur_pha = diff(ef)./160;
acc_time = cumsum(dur_pha(2:end));
acc_time = [0;acc_time];

changesped = diff(vr(ef));

% Central difference tangent at ef(6)-1 (same frame as release speed/height)
p1 = [py(ef(6)-2),pz(ef(6)-2)];
p2 = [py(ef(6)),pz(ef(6))];
rel_ang = rad2deg(atan2(p2(2)-p1(2),p2(1)-p1(1)));

plot(pyy(1:ef(2)),pxx(1:ef(2)),'b','LineWidth', 2, 'DisplayName', 'Double Support 1')
axis([-3, 0.5, -1.75, 2]);  % Set axis limits for both x and y from 0 to 4
axis square;  % Make the plot square
hold on
plot(pyy(ef(2):ef(3)),pxx(ef(2):ef(3)),'Color', [1, 0.5, 0],'LineWidth', 2, 'DisplayName', 'Left Support 1')
plot(pyy(ef(3):ef(4)),pxx(ef(3):ef(4)),'g','LineWidth', 2, 'DisplayName', 'Flight')
plot(pyy(ef(4):ef(5)),pxx(ef(4):ef(5)),'r','LineWidth', 2, 'DisplayName', 'Right Support 1')
plot(pyy(ef(5):ef(6)),pxx(ef(5):ef(6)),'Color',[139/255,0,139/255],'LineWidth', 2,'DisplayName', 'Release')
plot(pyy(ef(6):ef(6)+5),pxx(ef(6):ef(6)+5),'c','LineWidth', 2,'DisplayName', 'Discus Flight')
lgd=legend('show','NumColumns', 2, 'Location','northeast','Color', 'none','EdgeColor', 'none');
title('Overhead View')
xlabel('AP (m)')
ylabel('ML (m)')
set(lgd, 'EdgeColor', 'none');
tightfig()
saveas(gcf, [trialname,'_graph1.png'])
close all

plot(pyy(1:ef(2)),pzz(1:ef(2)),'b','LineWidth', 2)
axis([-3, 1, 0, 4]);  % Set axis limits for both x and y from 0 to 4
axis square;  % Make the plot square
hold on
plot(pyy(ef(2):ef(3)),pzz(ef(2):ef(3)),'Color', [1, 0.5, 0],'LineWidth', 2)
plot(pyy(ef(3):ef(4)),pzz(ef(3):ef(4)),'g','LineWidth', 2)
plot(pyy(ef(4):ef(5)),pzz(ef(4):ef(5)),'r','LineWidth', 2)
plot(pyy(ef(5):ef(6)),pzz(ef(5):ef(6)),'Color',[139/255,0,139/255],'LineWidth', 2)
plot(pyy(ef(6):ef(6)+5),pzz(ef(6):ef(6)+5),'c','LineWidth', 2)
title('Side-on View')
xlabel('AP (m)')
ylabel('VT (m)')
tightfig()
saveas(gcf, [trialname,'_graph2.png'])
close all

plot(pxx(1:ef(2)),pzz(1:ef(2)),'b','LineWidth', 2)
axis([-1.5, 1, 0, 2.5]);  % Set axis limits for both x and y from 0 to 4
axis square;  % Make the plot square
hold on
plot(pxx(ef(2):ef(3)),pzz(ef(2):ef(3)),'Color', [1, 0.5, 0],'LineWidth', 2)
plot(pxx(ef(3):ef(4)),pzz(ef(3):ef(4)),'g','LineWidth', 2)
plot(pxx(ef(4):ef(5)),pzz(ef(4):ef(5)),'r','LineWidth', 2)
plot(pxx(ef(5):ef(6)),pzz(ef(5):ef(6)),'Color',[139/255,0,139/255],'LineWidth', 2)
plot(pxx(ef(6):ef(6)+5),pzz(ef(6):ef(6)+5),'c','LineWidth', 2)
title('Front-on View')
xlabel('ML (m)')
ylabel('VT (m)')
tightfig()
saveas(gcf, [trialname,'_graph3.png'])
close all

plot(time(1:ef(2)),vr(1:ef(2)),'b','LineWidth', 2)
%axis([0, 1.5, 0, 25]);
ylim([0 25])% Set axis limits for both x and y from 0 to 4
axis square;  % Make the plot square
hold on
plot(time(ef(2):ef(3)),vr(ef(2):ef(3)),'Color', [1, 0.5, 0],'LineWidth', 2)
plot(time(ef(3):ef(4)),vr(ef(3):ef(4)),'g','LineWidth', 2)
plot(time(ef(4):ef(5)),vr(ef(4):ef(5)),'r','LineWidth', 2)
plot(time(ef(5):ef(6)),vr(ef(5):ef(6)),'Color',[139/255,0,139/255],'LineWidth', 2)
%plot(time(ef(6):end),vr(ef(6):end),'c','LineWidth', 2)
title('Discus Speed')
xlabel('Time (s)')
ylabel('Speed (m/s)')
tightfig()
saveas(gcf, [trialname,'_graph4.png'])
%print('-dsvg', 'graph4.svg')
close all

table1 = [speed_rel_r,rel_ang,speed_rel_z,speed_rel_y,rel_h];
table2 = [dur_pha,changesped,acc_time];
table2 = table2(2:end,:);

%copyfile('base_file.xlsx', 'new_file.xlsx');

% Create Excel ActiveX server
excel = actxserver('Excel.Application');
excel.Visible = false;  % Keep Excel invisible while working

% Open the workbook
workbook = excel.Workbooks.Open(fullfile(pwd, 'new_file.xlsx'));

% Get the 'sample' worksheet
sample_sheet = workbook.Sheets.Item('sample');

% Copy the sheet
sample_sheet.Copy([], sample_sheet);  % Copy after the source sheet

% Rename the copied sheet
copied_sheet = workbook.Sheets.Item(sample_sheet.Index + 1);
copied_sheet.Name = trialname;

range1 = copied_sheet.Range('A7:E7');
range1.Value = table1;

range2 = copied_sheet.Range('C53:E56');
range2.Value = table2;

% shapes = copied_sheet.Shapes; % Access the Shapes collection
% shapes.AddPicture(picturePath,1,1,1,100,-1,-1)

% Save and clean up
workbook.Save;
workbook.Close;
excel.Quit;
excel.delete;

