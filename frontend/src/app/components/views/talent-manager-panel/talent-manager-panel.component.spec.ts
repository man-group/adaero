import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { TalentManagerPanelComponent } from './talent-manager-panel.component';

describe('TalentManagerPanelComponent', () => {
  let component: TalentManagerPanelComponent;
  let fixture: ComponentFixture<TalentManagerPanelComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ TalentManagerPanelComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(TalentManagerPanelComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
