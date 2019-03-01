import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';

import { ApiService } from '../../../services/api.service';
import { HttpClientModule } from '@angular/common/http';
import { SelfNominateComponent } from './self-nominate.component';

describe('SelfNominateComponent', () => {
  let component: SelfNominateComponent;
  let fixture: ComponentFixture<SelfNominateComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      imports: [ HttpClientModule, RouterTestingModule ],
      declarations: [ SelfNominateComponent ],
      providers: [ ApiService ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(SelfNominateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
